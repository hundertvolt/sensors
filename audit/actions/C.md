# A-L C — phase C, the hardware rounds (HEAD b049724)

Sites read at `b049724`. Phase C (`audit/CONSOLIDATION.md` section 2: "Go-ahead per session. FRAM logs read and saved
first; lower levels run first; two-image GC proof; bench boot log and trigger timestamps; `reset_reason` codes proven;
twin corrected until it agrees; standard board state at start and end; bench Pi package check") runs after U37 (B5) and
before phase D. It is the collection point for every hardware duty planned elsewhere: the inventory below was built by
a scan of every earlier action file (`scratchpad/al/C/scan.py`, `ctx.py`, `th.py`: every action whose text names phase
C, "hardware in C", `Kind: hardware`, L3/L4, a wear marker, `mpremote`, a reflash or the bench, and every action whose
Site or Change touches `tests_hardware/{flash,bench,device_scripts,manual}` — 499 hits, 169 strong, 226 hardware-tier
test sites), each hit read, plus the 37 register blocks of `input_C.md` and the two its filter missed (LEAD/R27,
G8/R40; register fix 6). Where a block's C clause had no instrument in
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
  agent 2026-09-27); LEAD/R27 (State "applies to every phase-C round"; owner, 2026-09-08: "don't wait for
  something to maybe happen", "reproduce in a dedicated way, not full runs"); CLAUDE.md go-ahead rule (:284-293), FRAM rule and its caveat (:367-394), B.13 dead-man's switch
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
  a gated run only after a clean default run of the same image (the same image record) under the same conversation's
  go-ahead; a new conversation, or a changed image, runs the default tiers again first (owner D1, 2026-09-22, BACKLOG.md:
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
  moved firmware pin goes to the owner with the choice to hold the pin back (OR129.a (5), A.SDEP.08). A round never
  waits for a rare event it cannot trigger: it triggers the condition or records it as not reproducible with what was
  tried; a fault is reproduced with a small, bounded, dedicated script under `timeout`, never by repeating full suites;
  every failure that occurred is investigated to its cause (LEAD/R27, A.U26.81).
- **Blast**: callers — · generated the `dev` image, built per round · js — · tests the fixtures named (A.U26.03,
  A.U26.22, A.U26.79), the runners (A.U7.18, A.U7.14) · twin every row names its twin parameter; A.C.10 applies the
  corrections · docs A.U36.001's "How a round runs" is this frame's permanent text; the round records are audit files ·
  toml — · uart —.
- **Depends**: all of U0-U37 executed and A-C's delta list applied; A.U7.14, A.U7.18, A.U26.01-A.U26.03, A.U26.13,
  A.U26.22, A.U26.29, A.U26.79, A.U26.81, A.U36.001, A.S0930.06 (2).
- **Kind**: rule, hardware

### A.C.02 Round R0: prepare the bench host, no board
- **Why**: OR50.a (3)(b) "the bench Pi is checked for packages the current setup no longer installs in the hardware phase,
  with the owner's go-ahead" (owner, 2026-09-26); G1/R02 Req "record … the bench Pi's stale packages"; G1/R40 State
  "at the start of the first Phase C round the owner confirms, and `tests_hardware/README.md`'s bench facts record,
  whether the router's DHCP reservation is keyed to `eth0`'s MAC … and whether the BME688 on GP16/GP17 … is still
  attached (O.11, O.12)" (owner, 2026-09-25, OR32.a (3)); hand-offs to C: A.U21.18 (sudoers `--preserve-env`), A.U21.19
  (`nmcli connection edit` reads piped commands), A.U21.26 (passwordless sudo, `-n` semantics), A.U21.27 (picotool and
  sudo `secure_path`), A.U21.23 ("the first real run of `env --tier bench` against a fresh bridge … proves arm → create
  → poll → disarm"), A.U21.16 step 1 (GCC ≥ 14 build "else the bench Pi4 (GCC 14.2.0) in phase C"), A.U28.02 (bench uv
  matches the pin), the U28 installer row ("re-run `env --tier bench` on the bench Pi4 once; Playwright's `install-deps`
  failure is now fatal there"), A.U35.23/A.U8.16 (speed-probe bands on the bench Pi4 host, no board attached).
- **Site**: the bench Pi4 (host only; the board is not touched: no `mpremote`, no `picotool`, no device script);
  round record `audit/c/R0.md`; permanent results into `tests_hardware/README.md` bench facts table (A.U26.46) and Part N.
- **Change**: in order, under A.C.01 (1)-(2): (1) Host record: `/etc/os-release`, `uname -r`, `gcc --version`, `nmcli
  --version`, `sudo -V | head -1`, `picotool version`, `uv --version`, `node --version`; `uv --version` must equal
  `pyproject.toml`'s `[tool.uv] required-version` (A.U28.02), else the round stops for the owner. (2) Checks the
  installer made executable, run first: the bench tier's passwordless-sudo check (A.U21.26; `man sudo` read on the Pi for
  `-n`), `sudo -l` and `/etc/sudoers` read for `--preserve-env` acceptance (A.U21.18), `man nmcli` `edit` section read
  on the Pi (A.U21.19), `sudo sh -c 'echo $PATH'` and `command -v picotool` under sudo (A.U21.27); each result recorded;
  a result contradicting the installer's assumption is a delta for U21's code (A.C.10), not patched on the host.
  (3) `uv run toolchain/setup_toolchain.py env --tier bench`: with the existing `br0`, the run checks it (MAC warning
  path read, A.C.01 (2)); the fresh-creation proof of A.U21.23 runs only if the owner's go-ahead for this round names it,
  because it tears the bridge down first: B.13's switch armed by hand for the teardown, then the installer's own
  `_armed_recovery` arms, creates, polls and disarms, each state recorded (`systemctl is-active` before and after), and
  the new bridge's MAC checked against the uplink's. Playwright's `install-deps` must succeed or the run fails
  (A.U28 row). (4) Stale packages: `apt-mark showmanual`, `pip list --user`, `npm ls -g --depth=0`, `uv tool list` and
  `$PICO_TOOLCHAIN_DIR`'s entries compared with what `toolchain/versions.toml` (`apt_packages`, pins) and the env tiers
  install; the difference is listed with each package's last use found (`/var/log/apt/history.log`) and reported to the
  owner; nothing is removed unless the owner's go-ahead in this conversation names the packages (OR50.a (3)(b)).
  (5) If no GCC ≥ 14 trixie chroot build of A.U21.16 step 1 exists by now: both the rp2 firmware and the Unix port built
  on the Pi with `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND` removed in a throwaway worktree, under the toolchain lock;
  the compiler version and the warning count recorded; the result decides A.U21.16 step 2a/2b as a delta. (6) The speed
  probe (A.U8.16's monotonic probe) run on the Pi with no board attached, ten runs; its bands recorded against their
  Part N rows (A.U35.23: "the band values change only from those two measurements"). (7) The owner's two confirmations
  (DHCP reservation keyed to the uplink MAC; BME688 on GP16/GP17 attached or not) asked in this conversation and
  recorded, dated, in the bench facts table (A.U26.46). (8) The `env --tier bench` run of (3) records each step class's
  wall time (network, build) against A.U21.17's `tool.*` rows, and the L1 lwIP host hammer (A.U21.12/A.U21.13) runs once
  on the Pi, recording its slowest patched write against `l1.lwip_host_write_bound_ms`; both feed their Part N rows
  through A.C.10.
- **Blast**: callers — · generated — · js — · tests — (host checks; the installer's own tests are L0, U21) · twin — ·
  docs `tests_hardware/README.md` bench facts table rows (A.U26.46), Part N speed-probe rows, SPEC B.7.1 via A.U21.16
  · toml — · uart —. Wear: none on the board; host writes of one installer run and one firmware build.
- **Depends**: A.C.01; A.U21.13, A.U21.16, A.U21.17, A.U21.18, A.U21.19, A.U21.23, A.U21.26, A.U21.27, A.U26.46, A.U28.02,
  A.U8.16, A.U35.23.
- **Kind**: hardware (host)

### A.C.03 Round R1: first contact, then the release candidate's default run
- **Why**: OR28.a (1) "the dev bench's FRAM logs are read before clearing … at the start of the hardware session, which
  reflashes the board anyway" (owner, 2026-09-25); G1/R02 (image proof, lower levels first, default before gated);
  G1/R04 State "re-read bench NVM state" (owner, 2026-09-17); G1/R14, G5/R03, G7/R07 "each code is proven … on the dev
  bench" (owner, 2026-09-26, OR60 "b, but don't use FRAM … integrate it into the system service and its endpoints");
  G1/R20 (rungs on silicon, OR18.a); G4/R19 (the deinit script kept as a pin-move check); G4/R22 (bus clear, OR113.a);
  G4/R47 (bounds re-derived "on a named image"); G4/R62/G5/R23 (bench `ResetErrors` budget, OR72.a (5)); G4/R64
  (timing table measurements); G5/R45 ("float device scripts"); G6/R52/G4/R44 (L32 binding, A.C.13); G7/R04 (probes);
  LEAD/R06 (C-stack reading); owed rows handed to C: A.U12.01 (CRC32 per-call allocation "before and after"), A.U14.13
  (`constructed=N`), A.U18.33 (per-second `rssi` cost "measured in phase C"), A.U19.13 (serving-demand budget
  "re-derived with G4/R47's figures in phase C"), A.U30.04 (survivors bound now counting the VOC algorithm), A.U10.07
  (unfed boot stretches), A.U8.04/A.U8.11/A.U26.41 (3)/A.U26.54/A.U35.56 (l3/l4 and web tunables "measured in phase
  C"), A.U10.13, A.U9.04, A.U30.09 and SUPP_recovery's thresholds ("measurement owed" on the bench), BACKLOG "Not yet
  confirmed on silicon" (1) (SGP40 wrnno 35, today `W13`, per NTP outage, A.U2.13) and (2) (the flash tier ending on
  `hard_reset()`, HW.S28 "confirmed by Phase C's first full flash run").
- **Site**: the dev board and bench; `scripts/run_bench_hardware_suite.sh` (default flags only); round record
  `audit/c/R1.md`.
- **Change**: (1) First contact, on the image the board runs today, nothing written: `GET /system`, `GET /status` (the
  whole body, verbatim), `GET /sensors` (the SCD30 NVM-backed values: the bench NVM state G1/R04 asks for), `GET
  /networking` saved first over REST; then over the raw REPL (which stops `main.py`, CLAUDE.md), in one session that
  feeds the watchdog between reads (one script, or the dump scripts chained in one `mpremote` run with the feed kept),
  read only and in this order: `machine.reset_cause()` first, the raw FRAM dump (A.U26.22 (3)'s `fram_raw_dump.py`; if that image's frozen FRAM driver
  lacks the call the script uses, it reads with the READ opcode over plain `machine.SPI` and CS, read-only), every
  `config_*.cfg` printed verbatim (A.S0930.29's `config_files_dump.py`), and the CRC32 allocation probe of A.U12.01 on
  that image's frozen `crc_checks` (the "before" figure); all saved into the round record before anything else runs;
  the record states whether a reset landed between reads.
  (2) A.C.01 (3)-(6): lower levels, build, the planned image flash, image proof, standard state (the SCD30 snapshot of
  A.U26.79 compared with (1)'s values: a difference means the reflash or setup wrote SCD30 NVM and is reported).
  (3) The default run: `scripts/run_bench_hardware_suite.sh` (L0-L2, then L3 as its own step, then L4). Every new or
  changed L3/L4 test of the inventory marked "R1" runs here; the rows whose verdict the round record lists by name: the
  reset codes 2-6 and the BOOTSEL round trip with region 0 across it (A.U26.28, A.S0930.40), `erasefram`, near-miss
  words and the command concurrency/hang/power-loss/bus-hazard rows (A.S0930.28 (2)-(8), A.S0930.29 (2)-(5),
  A.S0930.39, A.S0930.40), the codes of A.C.12, the rungs (A.U26.34 automated rows, A.U13.R02 incl. the boot clear with
  SDA held at construction), the conformance probes with the BMP3xx reset key (A.U26.66, A.C.16), the ISL29125 rows
  (A.C.19's default half), the UART link in both CRC modes over the jumper and under API load (A.S0930.05, A.U26.82,
  A.U26.87), the lone-BMP3xx general call with its NAK count (A.U35.21), the FRAM hold, no-yield stretches, loop lag and
  C-stack scripts (A.U16.07, A.U31.05's first script, A.U31.06 (3), A.U30.18), the lwIP override hammer on the normal
  image (A.U26.85 (2)) — recorded as provisional: it counts as OR114.a (5)'s proof only after R4's control run
  reproduces the stall; a control run that passes every bound voids it (A.C.06) — the body-cap binding (A.C.13), the country reaction (A.C.14), the spoofing tests with the
  off-subnet attempt (A.U26.56 (3): works → an ordinary test; else the skip returns with the attempt's recorded reason),
  the watchdog-starvation test ending on a serving board (A.U26.25, A.U26.17), `float_boundary_2pow24.py` and
  `bus_deinit_is_a_noop_on_real_hardware.py` (G5/R45, G4/R19), the boot log (A.U26.41 (1)).
  (4) Measurements recorded with the image (build date, commit, `GC_THRESHOLD` in force): the CRC32 "after" figure
  (A.U12.01); `timer_alarm_pool_exhaustion.py`'s `constructed=N` with the image's other default-pool users
  (A.U14.13); the flash-tier heap figures — largest free block, survivors, the top 16 KiB — and SPEC I.1's post-build
  free heap on this named image (G4/R47, A.U26.48, A.U30.04, A.U19.13's `web.serving_demand_budget_b` basis); the
  `rssi` read cost: a read-only device script times 100 `network.WLAN(network.STA_IF).status("rssi")` calls on the
  still-associated radio (A.U18.33); the `ResetErrors` duration idle and under the item-32 reader counts, each after
  A.U26.22's save (G4/R62, G5/R23 — sets the bench budget, A.C.10); the idle loop share from A.U31.06's script with
  its load off (A.U8.11); the per-route request durations under the default run's load against `outer_cap_s`/
  `per_call_timeout_s` (A.U8.04); the engagement floors and `l4.dut_serving_after_sta_s` (A.U26.54, A.U26.41 (3)); the
  gaps between consecutive setup-unit lines of the boot log, stamped on arrival (A.U10.07's `boot.unfed_stretch_*`,
  the stamp resolution stated); every Part N row, product or test-tier, whose Basis says 'measurement owed' on the
  bench, L3 or L4 and whose test ran — including `stagger.min_read_separation_ms` (the longest single read per driver
  from the default run's reads, A.U10.13), `_MAX_SIGNAL_S` (the LED ramp's wall time under the bench API load, A.U9.04)
  and the recovery-ladder thresholds (the failure count at which each rung fired in the rung tests, SUPP_recovery)
  (A.U35.56's rule for bounds); and the loaded free-heap floor, `MemFree` polled during the default bench tier's load
  (A.U30.09, F.5.3); the SGP40 NTP-outage row (H78): UDP 123 blocked past `SGPWaitTimeNTP` by a bench `iptables` fault
  inside A.C.01 (2)'s armed switch, one wrnno 35 entry per outage, `ErrCount` rising per backup (zero wear).
  (5) Last, after the clean verdict is recorded: the deliberate red of A.C.18.
- **Blast**: callers — · generated the round's dev image · js — · tests every L3/L4 test of the inventory marked R1 ·
  twin the figures feed A.C.10 · docs via A.C.10 (SPEC F.1, F.3, F.5, I.1, C.7 budget; Part N; bench facts) · toml — ·
  uart —. Wear: flash filesystem — the planned image flash plus the default run's pinned prerequisites (A.U26.09's
  default row: the role-reversal fixture's SSID clear and restore, 2; the stale-credential recovery, 0 or 1; standard-state
  repairs only if the plan names `--repair-standard-state`); SCD30 NVM 0, at most 1 (A.U26.07); FRAM: any.
- **Depends**: A.C.01, A.C.02; A.C.12-A.C.16, A.C.18, A.C.19 (their default-run halves); every listed action executed.
- **Kind**: hardware

### A.C.04 Round R2: the operator round at the bench
- **Why**: G1/R40 "rig geometry (M1)" (owner, 2026-09-25, OR32.a (3)) and A.U26.42 "M1 before S3b"; G1/R20/LEAD/R29
  (SCD30 and FRAM unplug/replug, the SDA-to-GND step, A.U26.34 (2)); G1/R14/G5/R03 code 1 (power-on, a supply cut,
  A.U26.28 (2)); G4/R22 "hardware in C — one row measures it" (a held slave vs an MCU reset) and SUPP_recovery's row
  (what SCL/SDA do during `recover()`'s re-construction); G5/R35 "hardware in C — power-loss window and littlefs repair
  (G5.035)" (owner, 2026-09-26, OR69.a (3)) and A.S0930.25 ("S2's flush … atomicity is littlefs's and phase C's to
  show"); G7/R03 RF094 (SCD30 0x0010 persistence, A.C.15 (2)); G7/R32 "A real Safari/mobile pass is the owner's manual
  check in phase C" (owner, PQ10, 2026-09-26); A.U26.42 (4) (captive-portal observation); A.U19.07 (`web.max_head_bytes`
  "measurement owed on the bench"); G8/R18 "the three neu units and arzi against their TOMLs" (OR61.a "the owner builds
  and holds every unit", 2026-09-26).
- **Site**: `scripts/run_manual_hardware_tests.sh` (manual mode of L3/L4, harmonization 20); the owner's phones and
  desktop browsers; the bench Pi (packet capture); round record `audit/c/R2.md`.
- **Change**: on the R1 image, after R1's clean default run, the owner present: (1) M1 (A.U26.42 (3)): rig geometry and
  ambient condition written to the evidence directory and to `tests_hardware/README.md`'s rig section, dated. (2) The
  manual rung steps of A.U26.34 (2) — SCD30 unplug/replug, FRAM unplug/replug, SDA-to-GND — each judged with
  `confirm_pass()` against its `/status` oracle (`ResetReason`, `SysUptime`, the named catalog entries). (3) The
  power-cycle step of `manual_persistence.py` (A.U26.42 (2)): `ResetReason` 1 after power returns (A.U26.28), the
  FRAM-backed value survives, and A.C.15 (2)'s `AmbPres` readback before and after. (4) A.C.17's power-loss step.
  (5) Held-SDA observations with an oscilloscope only if the owner provides one at the bench: SCL/SDA during the boot
  clear (A.U13.R02's boot case) and during `recover()`'s re-construction (whether pico-sdk's `i2c_init()` clocks SCL);
  without a scope both rows stay BACKLOG owed rows with "needs a scope", never guessed. (6) The browser pass: the
  website served by the board over the bench AP on current Safari (macOS), Safari on iOS, Chrome and Firefox on
  Android and desktop Chromium/Firefox, desktop and phone widths: every page renders, every value shows, a no-op Apply
  answers "Unchanged" (no write), the history pills and the live refresh work; each result dated in SPEC H.1's floor
  sentence's evidence note (A.C.10); the captive-portal webview is observed on a phone during A.C.05's role-reversal
  hotspot window or A.S0930.29 (1)'s hotspot phase and recorded through `manual_wifi.py`'s text prompt (A.U26.42 (4)).
  During the browser pass `tcpdump -i br0 -s 0 -w <evidence>/heads.pcap host <DUT IP> and tcp port 80` runs on the Pi;
  the longest request head (request line plus headers, to the blank line) per browser is taken from it and recorded
  against `web.max_head_bytes` 2048 (A.U19.07). (7) The owner compares `devices/{klkizi,grkizi,schlafzi,arzi}.toml`'s
  wiring facts (buses, pins, frequencies, chip selects, IRQ pins) with each physical unit; no unit other than `dev` is
  flashed or connected over `mpremote` (CLAUDE.md :159-172); a mismatch is a TOML delta citing the unit as its origin
  (G8/R18); a match adds "(checked against the unit, owner, <date>)" to the TOML's origin comment (A.C.10).
  (8) A.S0930.29 (7)'s two power cuts: `erasefram` (FRAM only, no wear; evidence saved first) and `resetconfig` (config
  files saved first and restored verbatim afterwards, the bench joining the DUT's hotspot inside A.C.01 (2)'s armed
  switch).
- **Blast**: callers — · generated — · js — · tests the manual modules (A.U26.42, A.U26.34, A.U26.28's step, A.C.15 (2),
  A.C.17, A.S0930.29 (7)) · twin fidelity rows: flash power loss (silicon only), SCD30 0x0010 · docs `tests_hardware/README.md` rig
  section and bench facts, SPEC H.1 (browser floor evidence), Part N `web.max_head_bytes`, TOML origin comments (G8/R18)
  · toml `devices/*.toml` comments (A.C.10) · uart —. Wear: `manual_persistence.py`'s flash-config step 2 writes (A.U26.42
  (2): the value and its restore); A.C.17's scratch writes (≤ 60 and 3 removals over its three repetitions); the `resetconfig` cut: the deletions it
  completes plus one restore write per config file; power cycles are not wear.
- **Depends**: A.C.03 (clean default run of the same image); A.U26.28, A.U26.34, A.U26.42, A.C.15, A.C.17,
  A.S0930.29.
- **Kind**: hardware, doc

### A.C.05 Round R3: the gated wear run
- **Why**: owner D1 "spend flash/NVM writes, but only after a clean default run, so a gated failure is the gated test's
  own" (owner, 2026-09-22, BACKLOG.md:353-355); CLAUDE.md wear rule (:249-283, owned writes behind the marker);
  G3/R54 "Its one silicon run (S3b) is owed" (owner, 2026-09-15); G5/R34 RF207 "hardware in C — round trip on silicon"
  and G5/R45 RF216 "the config round trip is proven by an L3 device script" (owner, 2026-09-26, OR70.a (3)); G1/R28
  "hardware in C — confirm `machine.reset()` clears `_PHASE_DEACTIVATED`" (owner D03, 2026-09-26, OR72.a (6)); G7/R41
  (Altitude with `AmbPres` 0, owner OR100.a 2026-09-29); OR118.a (2) "a hardware reset test saves the dev board's config
  files first and restores them after (inside the same gated test), since the reset drops the bench unit's Wi-Fi" and
  OR124.a ("the reset includes Wi-Fi & Identity") (owner, 2026-09-30); G7/R03 (SCD30 argument-reaction row, A.C.15 (1));
  G6/R52 D4.219 hardware row (console output with a non-reading host, A.U19.23); A.U31.03 ("erase count per commit
  measurement owed, phase C"), A.U31.05 (`flash_write_loop_gap.py`), A.U35.40, A.U18.38, A.U15.07.
- **Site**: `scripts/run_bench_hardware_suite.sh` with the flags below; round record `audit/c/R3.md`.
- **Change**: on the R1 image, after a clean default run of that image under the same conversation's go-ahead
  (A.C.01 (7)) and R2's M1: (1) `--allow-persistence-write`: the flash then
  bench tier's owned-write tests — SCD30 read-while-write (A.U26.08 (1)), `resetconfig` at L3 over the scratch path
  with the hung-step watchdog test (A.S0930.28 (1), (6)), `resetconfig` at L4 with its in-test save of every
  `config_*.cfg` and verbatim restore, the bench joining the DUT's hotspot in between (A.S0930.29 (1); A.C.01 (2)'s
  switch armed across it), the config float round trip (A.U11.21), `flash_write_loop_gap.py` (A.U31.05), one boot with a
  config file forced into repair and the littlefs erase count of that commit recorded (A.U31.03), the torn-write reset
  race (A.U35.40), the role reversal's destructive stage 6 run as the round's last bench test, after every other gated
  and read-only row, with stage 8's check that the STA mode is back after the recovery reset (A.U26.39 (3)-(4):
  `_PHASE_DEACTIVATED` cleared by `machine.reset()`), the `HotspotPW` PUT rows
  (A.U18.38), the console row of A.U19.23 (`DebugLevel` 0 by PUT, a host process holding the CDC port open with DTR
  and never reading, the adversarial-client load of A.U19.23's L1 test replayed over HTTP for 60 s: no WDT reset,
  `ResetReason` unchanged, then `DebugLevel` 5 restored — 2 flash writes). Before stage 6 the record names its
  recovery: the USB raw REPL does not depend on the WLAN, so a board left with its WLAN deactivated is restored over USB
  (`config_files_restore.py` with the saved files, then `machine.reset()`, then a power cycle if that fails); a stage-8
  failure stops the round and goes to the owner (A.C.01 (9)). (2) `--allow-persistence-write
  --allow-scd30-extra-write`: the SCD30 hazard arm (A.U26.32), Altitude with `AmbPres` 0 (A.U26.72), the argument
  reaction of A.C.15 (1), and, only if the round's plan grants the two NVM writes, A.U15.07's `TempOffs` 0.53 written and
  read back as 0.53, then restored. (3) `--allow-neopixel-sweep --allow-persistence-write`: S3b, the ISL29125 envelope
  with `Overrange` (A.U26.11; G3/R54) and the hysteresis/PRST-window half of A.C.19.
- **Blast**: callers — · generated — · js — · tests the gated tests named · twin fidelity rows (SCD30 argument
  reaction, `_PHASE_DEACTIVATED` reset) via A.C.10 · docs `tests_hardware/README.md` budget table (A.U26.09) gains
  A.C.15 (1)'s, A.U15.07's and A.U19.23's rows · toml — · uart —. Wear: the sum of A.U26.09's README budget table for
  the flags used, stated in the round plan before the run and compared with the counts the fakes' write counters
  predict (A.U4.06); SCD30 NVM ≤ the table's `persistence_write` + `scd30_extra_write` rows.
- **Depends**: A.C.03, A.C.04 (M1 before S3b); A.U26.08, A.U26.09, A.U26.11, A.U26.32, A.U26.39, A.U26.72, A.U11.21,
  A.U15.07, A.U18.38, A.U19.23, A.U31.03, A.U31.05, A.U35.40, A.S0930.28, A.S0930.29, A.C.15, A.C.19.
- **Kind**: hardware

### A.C.06 Round R4: the reflash rows behind `flash_cycle`
- **Why**: OR112 "thoroughly test this in the hardware session" and OR114.a (5) "Phase C (OR112's 'thoroughly test'
  stands): first reproduce the stall on HEAD firmware …, then show no WDT reset, no VM stall and recovered service with
  the override"; OR115.a (4) (owner, 2026-09-30); G4/R44 State "hardware in C — the stall reproduced on HEAD firmware
  first, then dead- and slow-client page loads at the connection ceiling, arena/segment/queue limits at their edge, no
  WDT reset or write stall, page-load time before/after"; OR116.a/OR118.a (4)/OR123.a (3) "OR118.a (4)'s L4 run in the
  second mode (a reflash with `crc = "crc16"`) stays, behind `flash_cycle`" (owner, 2026-09-30); A.U26.14 (the reflash
  smoke test, `toolchain_reverify`).
- **Site**: `tests_hardware/bench/test_modlwip_send_stall.py` (A.U26.85's module), `bench/test_uart_link_crc16.py`
  (A.S0930.06), `flash/test_toolchain_flash_boot.py` (A.U26.14); round record `audit/c/R4.md`.
- **Change**: after a clean default run of the same standard image under this conversation's go-ahead (A.C.01 (7)): (1) the lwIP pair, in this
  order: `test_send_stall_on_the_unpatched_image` — the round builds the control image before the run in a throwaway
  worktree of its commit with the override call removed (A.U21.14's form, never committed; its image record carries
  `overrides: []` and `dirty: true`) and passes its path to A.U26.85's test through a new host option
  `--lwip-control-image <path>`; the test refuses (fails, never skips) a missing path or a record whose `overrides` is
  not empty; FRAM evidence saved, reflashed, the hammer and bounds run, the stall recorded (freeze length, `ResetReason`
  2 or not, the fresh `GET /` time), and in `finally` the release image recorded at start reflashed. No build flag is
  added; A.U26.85 (1)'s 'the test itself builds the control image' becomes 'the test takes the control image the round
  built' (co-lands with A.U26.85 and A.U21.14 — A-C merges); then `test_no_send_stall_with_the_override` on the
  release image, with page-load time and the cooperative retry's CPU cost recorded (A.U21.14). The pair order is the
  owner's "first reproduce … then show" (OR114.a (5)), kept inside this one round; R1's earlier run of the override test
  is the default suite's own pass (G1/R02: flash writes only after a clean default run). The pair drives each `ERR_MEM`
  source to its edge and records which fired: the arena (few connections, large route), the segment pool (many
  connections each queuing small writes, e.g. every page asset at once) and the per-pcb queue limit (one connection,
  many small writes to a non-reading peer); each case asserts the same pass criteria. If the dependency refresh moved the
  pin to a release carrying the upstream fix and removed the override (A.SDEP.13 (a)), the control image is the pinned
  v1.29.0 tree and the second half runs on the new pin's unpatched build. (2) The CRC16 run (A.S0930.06):
  the derived TOML with `crc = "crc16"` built to a temporary image, reflashed, the API-load link checks, the round's
  standard `.uf2` reflashed unchanged, image proof and `UARTLINK.Failures` 0. (3) The reflash smoke test (A.U26.14:
  retries only on picotool exit 249, passive end). (4) `--allow-toolchain-reverify` once (A.U26.14 (4); network fetches
  and builds, no board write). (5) Only if the round's plan includes it: H82 — the `stations` query without the 100 ms
  settle on a local-only image (A.U18.43, A.SDEP.17 W42), the station count checked, the round's standard image
  reflashed at once (A.C.01 (5)).
- **Blast**: callers — · generated the control and CRC16 images (temporary, never committed) · js — · tests as named ·
  twin — (the host lwIP hammer is U21's) · docs SPEC B.14 record of the proof (A.C.10); BACKLOG's lwIP owed row removed
  when both halves pass (A.U21.14) · toml — · uart — (CRC16 is Python-internal wiring; its Class B entry is
  A.S0930's). Wear: 5 flash cycles (2 + 2 + 1), each owned by its `flash_cycle` test; plus H82's 2 flash cycles when the
  round's plan includes it (A.U18.43's local-only image, reverted at once).
- **Depends**: A.C.03; A.U21.10, A.U21.13, A.U21.14, A.U26.14, A.U26.85 (its new `--lwip-control-image` option — A-C
  merges into A.U26.85), A.U18.43 and A.SDEP.17 (H82, only if planned), A.SDEP.13, A.S0930.06.
- **Kind**: hardware

### A.C.07 Round R5: the soak durations
- **Why**: G1/R22 "The 6 h run (S4) is release evidence and runs in Phase C" (owner, 2026-09-04, OR68.a (2)); G1/R30,
  G5/R07 "bench trigger timestamps over a long run" and G4/R64 (owner, 2026-09-26, OR47.a (3), C02); REF/R06 bench
  values for the FRC readiness defaults (A.U26.84, OR98.a/OR99.a); A.U15.20 (lost SGP40 samples, "phase C runs it");
  A.U26.35 (`l4.soak_request_failure_rate` "measured in phase C over the 6 h run"); A.SDEP.08 (6) ("run the flash, bench
  and mid-soak tiers against a `dev` build of the new pin", only if the pin moved).
- **Site**: `scripts/run_bench_soak_tests.sh --duration {short,mid,long}`; round record `audit/c/R5.md`.
- **Change**: on top of a clean bench run of the same image (G8/R41; the soak runner runs no lower levels, A.U7.18):
  `short` — SGP40 cadence (A.U15.20); `mid` — the liveness tests (A.U26.35); `long` (6 h, S4) — the liveness tests with
  the request-failure rate measured, the trigger spacing over the window (A.U26.41 (2), DebugLevel 5, the stagger read
  from the generated module), and the FRC readiness windows (A.U26.84) with the room condition the plan states (stable,
  unoccupied); each figure recorded with its image. A moved pin adds nothing here beyond running on it.
- **Blast**: callers — · generated — · js — · tests as named · twin the trigger distribution vs the twin's sequencer
  (A.C.10) · docs Part N rows (`sens.scd30_frc_*`, `l4.soak_*`), SPEC C.9.1's measured separation · toml — · uart —.
  Wear: none.
- **Depends**: A.C.03; A.U15.20, A.U26.35, A.U26.41, A.U26.84.
- **Kind**: hardware

### A.C.08 Round R6: the 12.4-day rollover run
- **Why**: G1/R23 "the run is scheduled in Phase C once that method exists" (owner, 2026-09-26, OR33.a (1); "(owner,
  2026-09-22) adapt now, measure later"); A.U26.36 ("a 13-day bench window, owner go-ahead").
- **Site**: `tests_hardware/bench/…::test_…rollover…` (A.U26.36's bench test) with `--allow-multi-day-rollover`; round
  record `audit/c/R6.md`.
- **Change**: on the release candidate image, after R5, the board touched by nothing else for the window (no other
  round runs meanwhile): A.C.01 (2)'s switch armed across the session-start fixtures (the stale-credential scan may take
  the AP slave down, A.U26.38) and disarmed once the hourly REST polls begin (they change no network state); the test
  runs until `SysUptime` passes `2**30 / 1000 + 3600` s. If a later delta changes tick-handling code (grep `ticks_` in the
  delta), the owner decides whether R6 is repeated; the record names the image it proved. The runner runs detached on
  the bench Pi (under `timeout` of the window plus margin); if the conversation that started it ends, nothing further is
  sent to the board or the bench network until a new conversation's go-ahead names R6, which then reads the runner's log
  and verdict.
- **Blast**: callers — · generated — · js — · tests A.U26.36 · twin the driven-time proofs are L1/L2 (LEAD/R04) · docs
  BACKLOG's G6 row removed (A.C.10) · toml — · uart —. Wear: none.
- **Depends**: A.C.07; A.U26.29, A.U26.36, A.U26.74.
- **Kind**: hardware

### A.C.09 Round R7: the release proof, last
- **Why**: OR40.a (3) "two images once, in the final hardware phase, as release proof — a `dev` image built without the
  threshold runs the full default flash and bench tiers first, then the normal image; the extra flash cycle is a
  planned prerequisite write" (owner, 2026-09-26); G4/R49; G1/R02 "The last rounds run the two-image GC proof … and
  record the timestamped boot log, trigger timestamps, every `reset_reason` code and the bench Pi's stale packages. F17's
  anomalies (BACKLOG item 44) close when the Phase C rounds show no unexplained reset" (OR60.a (4), OR47.a, OR50.a
  (3)(b)); LEAD/R02 (the round ends on the release image); A.U8.06 (UART tunables "re-measure owed on real hardware, with
  the two-image GC proof").
- **Site**: round record `audit/c/R7.md`; the no-threshold image from a throwaway worktree; the release image from the
  final commit.
- **Change**: only after every C delta is applied and one re-verification pass on that tree ended all green (A.C.11):
  (1) the no-threshold image — the final commit in a throwaway worktree with the generated boot entry's
  `gc.threshold(32768)` line removed from its template (`buildgen/codegen.py:704` at HEAD; never committed), built
  (record `dirty: true`), flashed, then the full default flash and bench tiers with `--image-record` pointing at that
  worktree's record: zero allocation markers in both hardware gates; (2) the release image built from the final commit,
  flashed, the full default flash and bench tiers again; the UART tunables' figures recorded on both images (A.U8.06).
  The record then lists: the timestamped boot log, the trigger distribution (R5's long run if the tree has not changed
  since, else re-run with `--soak-duration long`), every `ResetReason` observed across R1-R7 with its cause, the bench
  Pi's stale-package list re-checked (A.C.02 (4)), and the verdict on F17: every reset of phase C attributed, none
  unexplained — F17 closes; any unexplained reset is a new finding carrying its code (G1/R02). The board ends on the
  release image in the standard state.
- **Blast**: callers — · generated the release image · js — · tests the whole default flash and bench tiers twice ·
  twin — · docs SPEC I.4(f) release-proof record, BACKLOG item 44 and the S4/F17 rows removed (A.C.10) · toml — · uart —.
  Wear: 2 image flashes (planned prerequisite writes, OR40.a (3)) plus two default runs' pinned prerequisites.
- **Depends**: A.C.02-A.C.08, A.C.10, A.C.11 (1)-(3).
- **Kind**: hardware

### A.C.10 After each round: the findings pass A-C as a delta
- **Why**: OR106.a "New work found during execution (B0 measurements, B3 fault planting, hardware rounds) passes the
  same consolidation as a delta against the list before it is applied" (owner, 2026-09-29, OR108.a (1)); OR17.a (5) "the
  hardware rounds compare the results with the twin and correct it, repeating until they agree" (owner, 2026-09-25);
  OR29.a (3) (facts stored permanently, SPEC F / `tests_hardware/README.md`); OR30.a (3) ("no timeout is tightened
  without a measurement"); G9/R31 ("a delivered item leaves that list and every other place that names it").
- **Site**: the round record's findings list; the delta list A-C consolidates; after it: `digital_twin/` (fakes'
  parameters), `digital_twin/README.md` fidelity table, `SPECIFICATION.md` (F.1, F.3 table, F.5, I.1/I.4, I.6 `:5238-5243`,
  C.7, C.7.4, C.9.1, H.1, M.1.2, B.14), Part N rows, `tests_hardware/README.md` (bench facts, rig), `tests_hardware/
  error_log_helpers.py` (the `ResetErrors` budget), `devices/*.toml` origin comments, BACKLOG "Real-hardware work still
  owed".
- **Change**: per round result: a twin parameter or fidelity row changes only where the silicon evidence is solid
  (OR17.a (3)), the row's Status moving from assumption to measured, with the date and specimen; a Part N row whose
  test-tier or product value was measured takes Basis "measured (dev, <date>, <image build date>)" and a bound changes
  only as A.U35.56's rule allows; the `ResetErrors` bench budget becomes a tagged constant in `error_log_helpers.py`
  from R1's figures plus a stated margin, and BACKLOG item 32 closes; each delivered BACKLOG owed row is removed with
  every citation of it (G9/R31); a defect goes the OR12.a path. The lower levels touched by a delta run at both GC
  stages before the next round (A.C.01 (4) does it anyway). Permanent text written here cites no audit ID and carries
  "(agent, <date>)" for measured facts and their source run.
- **Blast**: per delta, filled by A-C when it consolidates it (callers, generated, js, tests, twin, docs, toml, uart) ·
  each delta's blast is searched as in every unit (brief step 4).
- **Depends**: the round it follows.
- **Kind**: rule, doc, code, test

### A.C.11 Close phase C
- **Why**: OR5.a (2) "a real-hardware phase on the dev bench that closes every item parked for real hardware" (owner,
  2026-09-25); OR8.a "the release is final once it passes"; OR9.a (a pass after the last fixes, until all green); G9/R24
  (every item terminal); LEAD/R15 ("the owner's agreement that the audit is finished").
- **Site**: the inventory below; BACKLOG "Real-hardware work still owed"; the register's `moved-to-hardware` entries.
- **Change**: (1) Every inventory row is delivered (its round record names the verdict) or, only by the owner's decision
  in a round conversation, re-queued as a BACKLOG owed row with its reason; H76 (the UART babbling peer) stays owed
  (owner, 2026-09-25: the bench has no such peer). (2) Every register entry `moved-to-hardware` becomes terminal from
  its round result. (3) After the last delta of R1-R6: one re-verification pass by A.U37.07's rule ends all green on the
  final tree, then R7 runs (A.C.09); a finding in R7 is a delta, then the pass and R7 repeat. (4) The owner is told the
  hardware phase is complete and gives the agreement that opens phase D (A.U37.15-A.U37.16).
- **Blast**: callers — · generated — · js — · tests — · twin — · docs BACKLOG owed section (only re-queued rows and H76
  remain) · toml — · uart —.
- **Depends**: A.C.02-A.C.10.
- **Kind**: rule, hardware

### A.C.12 Reach reset codes 0, 9, 10+p and 20 on silicon
- **Why**: G5/R03 / G7/R07 "each code is proven at L2 and on the dev bench" — OR60.a (4) "each code is proven at L2 and
  on the dev bench (with the hardware go-ahead)" (owner, 2026-09-26); harmonization 45 (OR77, OR79): a real-bench
  injection is attempted, and an exception stays only if the attempt shows unreasonable effort or no case beyond L1-L3.
  A.U26.28 covers codes 1-6 and leaves "boot-failure (10 + phase) … listed as a structural exception" and does not
  reach 0, 9 or 20; codes from U11's design block (0 unknown, 10 + p boot failure), A.S0930's `_RR_COMMAND_INCOMPLETE`
  (9), A.U30.19's `_RR_STACK_EXHAUSTED` (20). All four are reachable from a device script without a product hook: region
  0 is writable from the raw REPL (`machine.mem_backup(0)`, a static memoryview, `extmod/machine_mem.c:134-149`,
  v1.29.0); the phase marker is written by the generated `main()` itself (A.U11.06); a test-side rebinding from outside
  is the technique A.S0930.28's hang test already uses.
- **Site**: `tests_hardware/bench/test_reset_reasons.py` (created by A.U26.28), new device scripts
  `tests_hardware/device_scripts/reset_code_invalid_record.py`, `reset_code_command_incomplete.py`,
  `reset_code_boot_phase_hang.py`, `reset_code_stack_exhausted.py`; the E.6 exception list row A.U26.28 adds.
- **Change**: four bench tests, each saving FRAM evidence first (A.U26.22), running its script through
  `run_isolated_expect_reset()`, waiting passively for the production boot to serve, reading `GET /status`
  `ResetReason`, and restoring serving in `finally` (`restore_board_to_serving()`): (1) `test_an_invalid_record_reads_as_
  unknown` — the script writes a non-magic word into `mem_backup(0)[0]` and calls `machine.reset()`; expect 0.
  (2) `test_an_incomplete_command_is_attributed` — the script builds the real generated system over a scratch config
  path (A.U26.10) as A.S0930.28 does, rebinds from outside the FRAM erase's per-unit write so unit 2 raises
  `OSError(EIO)`, and calls `_system_cmd_callback("erasefram")`; expect 9 and, from the raw dump after the boot, every
  chunk either blank or holding its saved content (no torn chunk). No flash write (FRAM only). (3) `test_a_hang_in_boot_
  phase_p_is_attributed` parametrised over the five phases 1-5 (construction, setup batch, task starts, timer starts,
  first NTP force sync, U11's numbering): the script runs the generated `main(watchdog=machine.WDT(timeout=8000),
  cfg_path=<scratch path>)` (A.U20.02; A.U26.10; `cfg_path` stays a `main()` option per OR126.a (1)) with one callee of that phase rebound from outside to `time.sleep_ms(10000)` (a driver constructor, one
  setup unit, one task starter, one timer starter, the force-sync call — each chosen at execution from the generated
  module), so no feed follows and the watchdog resets with the phase marker set and no record; expect 10 + p. (4)
  `test_a_c_stack_exhaustion_is_attributed` — the script builds the system over a scratch `cfg_path` (A.U26.10), rebinds one supervised reader's read
  coroutine from outside to recurse until the stack check raises `RuntimeError`, and lets the supervisor escalate;
  expect 20. Each script is run through the twin runner first (A.U26.05, A.U35.49): (1), (2) and (4) agree with A.U25.55's
  L2 codes; (3)'s twin record is the exception "watchdog reset needs silicon" (the twin WDT never resets, A.U25.55). A
  code the attempt cannot reach returns to the E.6 exception list with the attempt's recorded result (OR77.a);
  A.U26.28's boot-failure exception row is replaced by this attempt (A-C merges).
- **Blast**: callers — · generated read through the generated `main()`/`build_system()` (A.U20.02) · js — · tests new
  L4 (four tests, bench module of A.U26.28), four device scripts (the pin guard A.U26.44 and the wear guard A.U26.06 see
  them: no persisting write, no marker); A.U26.06 (2)'s persisting-call set also counts a generated `main(` call without
  a scratch `cfg_path` (co-lands with A.U26.06 — A-C merges); `tests_scripts/test_bench_restores_serving.py` covers the module ·
  twin A.U25.55's code list, fidelity row "watchdog reset: silicon only" · docs `tests_hardware/README.md` "Reset codes
  proven on the bench" table (A.U26.28) gains 0, 9, 10+p, 20; E.6 exception list · toml — · uart —. Wear: none (FRAM only).
- **Depends**: A.U11.05, A.U11.06, A.U20.02, A.U26.05, A.U26.06, A.U26.10, A.U26.22, A.U26.28, A.U30.19, A.S0930.13-.17, A.S0930.28.
- **Kind**: test, hardware

### A.C.13 Prove on silicon that an oversized body is refused unread
- **Why**: G6/R52 "the 2,048 B cap's binding is confirmed at L4" (owner, 2026-09-26, OR52.a (3)); G4/R44 State
  "hardware in C — raised PCB count and body-cap binding (L32)"; L32 "Body-cap binding never hardware-confirmed"
  (DECISION_PROVENANCE, keep). SPEC:5238-5243 at HEAD: "a socket cannot distinguish 'buffered then rejected' from
  'rejected unread' … The binding itself stays a mock-tier and source-level claim". A socket can, by timing: Microdot reads
  the body only when `content_length <= Request.max_body_length` (`ext/microdot.py:425-430`) and answers 413 when
  `content_length > max_content_length` (`:1443-1445`), and the webserver binds both to one value
  (`src/asy_webserver_service.py:363, 370`); a 413 that arrives while the body is still unsent can only come from a body
  never read.
- **Site**: `tests_hardware/bench/test_network_resilience.py`, after `test_put_body_cap_boundary_is_exact_over_the_
  normal_network` (`:787`).
- **Change**: `test_an_oversized_body_is_refused_before_it_is_read(dut_ip)`: the cap read from `src/` by `ast`
  (A.U26.49's pinned-value rule, not the `:768` copy); a raw socket sends `PUT /sensors HTTP/1.1`, `Host`,
  `Content-Type: application/json`, `Content-Length: <cap + 1>` and the blank line, no body byte; asserts a complete
  `413` response within `l4.cap_binding_answer_s` (Part N row, basis "estimated (agent, <date>) — measured in phase C";
  a Part N relation row: `l4.cap_binding_answer_s` < `web.per_call_timeout_s`, checked by A.U8.02's relation checks)
  while nothing more is sent. Control arm in the same test: `Content-Length: <cap>` with no body gets no response within
  that window (the server is waiting in `readexactly()`), and the test closes the socket before `web.per_call_timeout_s`
  elapses (the reader is wrapped in `_TimeoutStreamProxy(reader, self._per_call_timeout_s, …)`,
  `src/asy_webserver_service.py:705`, default 5.0 s at `:321`). The `/status`
  `MemFree` read before and right after the refused request differs by less than the cap (a second, independent
  oracle, recorded). Its host logic runs against the twin first (OR29.a (4)).
- **Blast**: callers — · generated — · js — · tests new L4 test (unmarked: a refused PUT persists nothing, OR49.a (2);
  `_JUSTIFIED_UNMARKED` in `tests_scripts/test_persistence_write_marker_completeness.py` gains its reason "refused
  unread: nothing persists") · twin the same test against the twin (`TwinBoard`, A.U26.05) · docs SPEC I.6
  `:5238-5243` "never a hardware-confirmed one" → the silicon result with its date (A.C.10); Part N row · toml — · uart —.
  Wear: none.
- **Depends**: A.U19.07 (the stream guard in front of `readexactly()`), A.U8.02 (relation checks), A.U26.05, A.U26.49,
  A.U11.08 (`MemFree`).
- **Kind**: test, hardware

### A.C.14 Record what the radio does with a malformed country code
- **Why**: G6/R28 RF213 "hardware in C: the driver passes any two bytes to the firmware's `country` iovar and ignores
  the reply (`cyw43/src/cyw43_ll.c:1843-1865`, `055d642`), so nothing in the driver raises; the C row measures what the
  radio firmware does — if the radio raises, `_trigger_sta_connect()` feeds `hw_op_failed`" (agent, 2026-09-28).
  Verified: `network.country()` refuses only a length ≠ 2 (`extmod/modnetwork.c:134-146`, v1.29.0) and the code reaches
  the radio at radio-on (`cyw43_ll_wifi_on()`, `cyw43/src/cyw43_ll.c:1843-1866`). The only instrument that called
  `network.country()` with a malformed value, `wifi_country_hostname_edge_values.py`, is deleted by A.U26.20 (its "XX"
  is MicroPython's own default, N.53), so this row has no instrument at HEAD+plan.
- **Site**: new `tests_hardware/device_scripts/wifi_country_code_reaction.py`; `tests_hardware/flash/
  test_bus_electrical_timing.py` beside `test_single_precision_float_boundary_at_2pow24` (`:69`).
- **Change**: the script (header ≤ 3 lines; arms the watchdog as every device script; feeds between steps): for each of
  `"ZZ"` (ISO-shaped, not assigned), `"12"`, `"\x01\x02"`: `network.WLAN(network.STA_IF).deinit()`, `network.country(v)`,
  a fresh `WLAN(STA_IF).active(True)`, one `scan()`; prints `FACT country=<repr> set=<ok|exc> radio_on=<ok|exc type>
  scan_count=<n> readback=<repr>`; finally restores the bench TOML's country (from the rendered bench facts, A.U26.44)
  and radio-on succeeds, printed as `FACT restored=<ok>`. The test judges only that every step reported and the restore
  succeeded (the facts are the deliverable, A.U26.68's shape) and records them; `restore_board_to_serving()` after.
  The sequence (deinit, then radio-on applying the new country) is checked against `extmod/network_cyw43.c` at the pinned
  tag before the script lands.
- **Blast**: callers — · generated — · js — · tests new L3 test and script (no write: `network.country()` writes no
  flash; wear guard and pin guard see it) · twin `digital_twin/network.py` models the recorded reaction "identically"
  (G6/R28 Req) once measured (A.C.10) · docs SPEC C.7.4 (the country bullet A.U14.37 writes) gains the silicon result,
  dated · toml — · uart —. Wear: none.
- **Depends**: A.U14.37, A.U26.20, A.U26.44, A.U26.68; U6/U18's ISO-shape check (RF213).
- **Kind**: test, hardware

### A.C.15 Measure the two SCD30 assumption rows
- **Why**: G7/R03 "A reaction the datasheet leaves open … is backed by a measurement or marked an assumption with a
  BACKLOG real-hardware row" and State "hardware in C (assumption rows)"; RF094 "the pressure value's persistence
  becoming an assumption row with a hardware row in C" (Interface Description v1.0 p8 says only "Continuous measurement
  status is saved in non-volatile memory"); A.U25.01's rows "SCD30 reaction to a wrong argument CRC or an out-of-range
  interval" and "SCD30 0x0010 pressure persistence". No earlier action writes an instrument for either (A.U26.66's SCD30
  probe reads version, interval, data-ready, measurement CRCs, NACK before command, soft-reset time only).
- **Site**: (1) new `tests_hardware/device_scripts/scd30_argument_reaction.py` and a test in `tests_hardware/flash/
  test_chip_conformance.py` (A.U26.66's gate file); (2) `tests_hardware/manual/manual_persistence.py`'s power-cycle step
  (A.U26.42 (2), A.U26.28's code-1 step).
- **Change**: (1) `@pytest.mark.persistence_write @pytest.mark.scd30_extra_write test_scd30_argument_reaction_is_
  recorded(board, scd30_measuring)`: the script (raw `machine.I2C` at the bench facts' bus and address, A.U26.44) reads
  the measurement interval (0x4600 read); sends 0x4600 with the current interval and a deliberately wrong argument CRC,
  reads the interval back and times the next two data-ready periods; sends 0x4600 with 0 and a correct CRC, reads back
  and times again; restores the original interval with a correct write if either changed it, in `finally`; prints
  `FACT wrong_crc_accepted=<y|n> zero_interval_accepted=<y|n> restored=<ok>` and each read value. The host test asserts
  `restored=ok` and the interval equals the start snapshot (A.U26.79), records the facts. Budget row in A.U26.09's table:
  at most 3 SCD30 NVM writes (an accepted wrong-CRC write of the unchanged value, an accepted 0, its restore). The
  script runs through the twin first (A.U26.05): the fake ignores both today (the assumption), so a silicon "accepted"
  is exactly the divergence the row exists to catch. (2) In the power-cycle step: `GET /sensors` SCD30 `AmbPres` before
  the cut and after power returns and the board serves; the step records both, and whether the product's boot sends
  0x0010 (read from `src/asy_scd30_driver.py`'s `setup()`/`_init_scd()` at execution and written into the step's text);
  no write by the step.
- **Blast**: callers — · generated — · js — · tests new gated L3 test; the manual step · twin `digital_twin/
  _scd30_chip.py` follows the measured reaction and the 0x0010 row's Status moves to measured or "not relied on: the boot
  sends 0x0010" (A.C.10) · docs fidelity table rows, `tests_hardware/README.md` budget table (A.U26.09), SPEC M-less SCD30
  facts in C.3 (A.U15.08's comment) · toml — · uart —. Wear: (1) ≤ 3 SCD30 NVM writes behind both flags; (2) none.
- **Depends**: A.U25.01, A.U25.12, A.U15.08, A.U26.05, A.U26.09, A.U26.42, A.U26.44, A.U26.66, A.U26.79.
- **Kind**: test, hardware

### A.C.16 Check register volatility and record the bench SCD30 NVM state
- **Why**: G1/R04 State "hardware in C — re-read bench NVM state and register volatility (G3.076)"; Req "BMP3xx and
  ISL29125 configuration registers are volatile (reset at power-on) … SCD30 NVM values persist across power cycles, so
  tests never assume factory defaults" (owner 2026-09-17 wear rule; datasheets: BMP388 "A power-on reset generator …
  resets the logic circuitry and the register values" and "softreset … all user configuration settings are overwritten
  with their default state", `dstxt/bmp3xx__bst-bmp384-ds003.txt:401, 899-903` (the dev board's part), as BMP388
  `ds001:454, 1717-1718`; ISL29125 "Write 46h to register 0x00
  … the device will reset all registers to their default states", `dstxt/isl29125__…:684`). A reset command is the
  zero-wear discriminator: an NVM-backed setting survives its chip's soft reset (SCD30's do, SUPP_recovery A.U15.R01),
  a volatile register returns to its default. The ISL29125 probe already reads the configuration before and after its
  reset (`isl29125_mock_conformance_probe.py:88-91`, keys A03-A05); the BMP3xx probe of A.U26.66 does not.
- **Site**: A.U26.66's BMP3xx probe script; `tests_hardware/README.md` bench facts table (A.U26.46).
- **Change**: (1) The BMP3xx probe gains two keys: after its existing reads it writes distinctive values to OSR (0x1C)
  and CONFIG (0x1F), reads them back (`C01_osr_config_written`), issues the soft reset (0xB6 to CMD 0x7E), waits the
  datasheet's start-up time and reads both again (`C02_osr_config_after_softreset`), expecting the datasheet defaults;
  both keys are protocol keys compared with the twin (the fake's reset models the defaults; a mismatch is a fidelity
  finding). (2) The bench SCD30 NVM state — `MeasInt`, `TempOffs`, `Altitude`, `AmbPres`, `SelfCal` from R1's first
  contact and from A.U26.79's snapshot — is recorded as a dated row of the bench facts table, the text saying these
  values persist across power cycles and tests take them from the snapshot, never from factory defaults.
- **Blast**: callers — · generated — · js — · tests A.U26.66's BMP3xx probe and its twin run · twin `digital_twin/`
  BMP3xx chip fake reset defaults (checked, changed only on a divergence) · docs bench facts row; CLAUDE.md wear rule's
  "FRAM writes are not wear" sentence is U36's (G1/R04) · toml — · uart —. Wear: none (RAM registers).
- **Depends**: A.U26.46, A.U26.66, A.U26.79; A.C.03 (1).
- **Kind**: test, hardware, doc

### A.C.17 A power cut during a config write leaves a loadable file
- **Why**: G5/R35 "hardware in C — power-loss window and littlefs repair (G5.035)"; Req "A power loss between the
  response and the deferred write may lose that change silently; the write never corrupts (littlefs commits a file
  atomically at close, `lib/littlefs/lfs2.h:333,356`), and the next boot repairs what an interrupted write left" (owner,
  2026-09-26, OR69.a (3), C01); A.S0930.25 (S2's flush "atomicity is littlefs's and phase C's to show"). Only a real
  supply cut tests it: a watchdog or `machine.reset()` restarts the RP2040, not the flash chip, and the bench has no
  switched supply (BACKLOG item 8, owner-settled), so it is an operator step.
- **Site**: new `tests_hardware/device_scripts/config_write_loop_scratch.py` and `config_scratch_readback.py`; a new
  step in `tests_hardware/manual/manual_persistence.py`.
- **Change**: the step states its budget and asks the operator to confirm before it starts ("up to 20 scratch flash
  writes and one removal"): the first script builds a `ConfigManager` over `config_HWTEST_POWERLOSS.cfg` with a
  two-field schema and writes alternating values through the product path (`write_config()` then `flush_pending()`),
  printing `WROTE <n> <value>` after each, at most 20 writes, feeding the watchdog; the operator pulls the USB supply
  while the lines are still arriving; after power returns and the production boot serves (`ResetReason` 1), the second
  script (read-only, then its removal as the allowed scratch cleanup, OR38.a (4)) loads the file through
  `ConfigManager.setup()`'s read path and prints whether it parsed, its values and whether a repair was needed; the step
  judges with `confirm_pass()`: the file parses and holds the last reported value or the one before, never a truncated
  or mixed file; the scratch file is gone afterwards. The step repeats three times with the cut at different points.
- **Blast**: callers — · generated — · js — · tests the manual step and two scripts; A.U26.06 (2) gains a manual branch:
  a persisting script whose only runners are in `tests_hardware/manual/*.py` passes when each running step prints its
  write budget and takes the operator's `confirm()` before the script runs (checked by `ast`: a `confirm(` call precedes
  the run call in the step function), listed in `_MANUAL_PERSISTING_STEPS = {<script>: <reason>}`; a tmp manual step
  without the confirmation fails (bite) (co-lands with A.U26.06 — A-C merges) · twin
  fidelity row "flash-filesystem power loss: silicon only" (A.C.10) · docs SPEC F.2/C.7.3's power-loss sentence gains the
  silicon result, dated · toml — · uart —. Wear: ≤ 60 scratch flash writes and 3 removals over the three repetitions.
- **Depends**: A.U11.28 (deferred flush), A.U26.06 (its manual branch), A.U26.18, A.U26.42.
- **Kind**: test, hardware

### A.C.18 The hardware allocation gates fail on a real caught failure
- **Why**: A.U35.05 (3) "the real-silicon arm goes to the phase-C queue (A.U35.54) as one deliberate check"; A.U20.04
  "phase C confirms a caught allocation failure under heap exhaustion logs 'memory allocation failed' on silicon";
  CLAUDE.md memory rule (the four gates match `MemoryError` or `memory allocation failed`; the suite's own injections
  stay worded clear of what the gates grep for).
- **Site**: A.U35.05's throwaway worktree only (a planted device script, never committed); the flash and bench runners.
- **Change**: in the throwaway worktree, a planted script allocates 4 KiB blocks into a list until `MemoryError`, then
  prints `str(e)` (the product's logging form), releases the list and prints `DONE`; one planted flash test and one
  planted bench test run it through `run_isolated()`. Run once through `scripts/run_flash_hardware_suite.sh -k <planted>`
  and once through the bench runner the same way: both verdicts must be red naming the allocation marker
  (`tests_hardware/harness.py` `MEMORY_ERROR_MARKERS`), and the printed text must contain `memory allocation failed` on
  silicon (the emergency exception buffer of A.U20.04 in effect). Expected red, recorded as such in R1's record; a green
  verdict is a gate defect fixed in the gate (A.U35.05). Worktree removed afterwards.
- **Blast**: callers — · generated — · js — · tests none committed · twin the same plant's twin arm is A.U35.05 (3) ·
  docs — · toml — · uart —. Wear: none.
- **Depends**: A.U20.04, A.U26.47, A.U35.05, A.C.03 (runs after R1's clean verdict).
- **Kind**: test, hardware

### A.C.19 Re-measure the ISL29125 behaviour rows; correct the stale comment
- **Why**: G3/R46 "the behaviour is measured on silicon and recorded in SPEC M.1.2 with date and specimen count; the twin
  models every row; the PRST unit `persist_for_interval()` depends on is asserted, the restart question reported only; a
  second specimen or a changed rig or cover triggers re-measurement, hysteresis band and PRST windows included" (fact,
  measured 2026-09-12/13 on one board); State "work: hardware in C". At HEAD the PRST unit is already asserted:
  `tests_hardware/device_scripts/isl29125_real_irq_edge.py:117-121` prints `RESULT: FAIL … persist_for_interval()
  assumes whole RGB cycles` whenever `persist_unit=rgb_cycles` is absent — `inconclusive` included (`:61`) — and the
  host test fails on any FAIL line. Only the host comment `tests_hardware/flash/test_bus_concurrency.py:95-97` ("Both
  are reported … neither gates the pass") is stale.
- **Site**: `tests_hardware/flash/test_bus_concurrency.py:95-97` (comment); SPEC M.1.2 (`SPECIFICATION.md:6660-`),
  M.1.4; `digital_twin/README.md` fidelity table.
- **Change**: (1) DONE-AT-HEAD: `isl29125_real_irq_edge.py:117-121` fails unless the part counts whole RGB cycles
  (inconclusive included). Only the comment `flash/test_bus_concurrency.py:95-97` changes: 'Also measures … Both are
  reported … neither gates the pass.' → '# The script fails unless PRST counts whole RGB cycles, the unit
  persist_for_interval() assumes; / # whether a CONFIG1 write restarts a conversion is reported only.' The
  CONFIG1-restart facts (the probe's G01/G02 keys) stay reported only. (2) In R1 the probe (moved into
  `flash/test_chip_conformance.py` by A.U26.66) and this test run; in R3 the S3b envelope measures the hysteresis band
  and PRST windows. Each M.1.2 row is compared with the result: a row confirmed gains "confirmed <date>, one specimen
  (the dev breakout)"; a changed rig (R2's M1 geometry differs from the recorded one) or a changed cover makes the
  hysteresis band and PRST windows re-measured values, dated. (3) The twin's `_isl29125_chip.py` models every measured
  row; the CONFIG1 restart row stays "assumption, never tuned to" unless the probe's facts settle it.
- **Blast**: callers — · generated — · js — · tests one comment (no behaviour change) · twin
  `digital_twin/_isl29125_chip.py` via A.C.10 · docs SPEC M.1.2 dates and specimen count, M.1.4, fidelity rows · toml —
  · uart —. Wear: S3b's gated writes (A.C.05); the probe and the IRQ-edge test write none.
- **Depends**: A.U26.11, A.U26.42, A.U26.66, A.U25.01.
- **Kind**: hardware, doc

## Hardware-duty inventory

Every hardware duty found in `audit/actions/*.md` (U0-U36b, U8C/U8C2, SUPP_*) and in the 37 input blocks plus LEAD/R27
and G8/R40. "own": a run,
measurement or record this file plans as a step or instrument; "co-land": a test or fixture an earlier action writes,
executed by the named round's suite run with no further step. Rounds: R0 host (A.C.02), R1 default (A.C.03), R2
operator (A.C.04), R3 gated (A.C.05), R4 flash cycles (A.C.06), R5 soak (A.C.07), R6 rollover (A.C.08), R7 release
proof (A.C.09); "every" = every round (A.C.01).

| # | duty | source action(s) / register | level · gate | round | own / co-land |
|---|---|---|---|---|---|
| H01 | owner go-ahead in the round's conversation; round plan (order, outcomes, wear, twin parameter) | CLAUDE.md :284-293; G1/R02; OR8.a, OR17.a (4) | — | every | own (A.C.01) |
| H02 | FRAM `errcount` and raw FRAM read and saved before anything writes; the first-chunk caveat | A.U26.22, A.U36.002, CLAUDE.md :367-394; OR28.a (1) | L3/L4 | every | co-land (fixture) + own (A.C.01 (3)) |
| H03 | lower levels L0-L2 at both GC stages first; never clean when skipped | A.U7.18, A.U7.14; OR45.a (2)(a) | L0-L2 | every | co-land |
| H04 | image record and image-identity fixture (`buildDate`, lwIP ensemble) | A.U26.02, A.U26.03; G1/R02 | L4 | every | co-land |
| H05 | standard board state at start and end; timed-out script interrupted | A.U26.79, A.U26.12; LEAD/R02 | L3/L4 | every | co-land |
| H06 | timestamped boot log saved | A.U26.41 (1), A.U26.26; G1/R30, G5/R05 | L4 | every | co-land |
| H07 | bench network: switch armed around every `br0`/slave change; `br0` MAC equals the uplink's | CLAUDE.md :295-306, SPEC B.13; A.U21.23 | host | every | own (A.C.01 (2)) |
| H08 | pre-audit image: `/system`, `/status`, `/sensors`, `/networking`, `reset_cause()`, raw FRAM, config files | OR28.a (1); G1/R04; A.S0930.29's dump script | L3/L4 read-only | R1 | own (A.C.03 (1)) |
| H09 | CRC32 per-call allocation before (pre-audit image) and after | A.U12.01 | L3 | R1 | own |
| H10 | reset codes 2-6 and BOOTSEL round trip (region 0 across `reset_usb_boot()`) | A.U26.28, A.U11.05 design note, A.S0930.30; G1/R14, G5/R03, G7/R07 | L4 | R1 | co-land |
| H11 | reset code 1 (power-on) | A.U26.28 (2), A.U26.42 (2) | manual | R2 | own step |
| H12 | reset codes 0, 9, 10+p, 20 | G5/R03, OR60.a (4), harmonization 45 | L4 | R1 | own (A.C.12) |
| H13 | `resetconfig` / `erasefram`: function, near-miss words, states, bus hazard, watchdog takeover and hung step, power loss per step (codes 7, 8) | A.S0930.28, A.S0930.29; OR117-OR122, OR124 | L3/L4 | R1 (ungated rows), R2 (the two manual power cuts), R3 (`resetconfig`, `persistence_write`, configs saved and restored) | co-land |
| H14 | `reboot`/`bootloader` through the controlled sequence, timing bounds, at-once race (codes 3, 4) | A.S0930.39, A.S0930.40, A.U23.33; OR126.a (3), OR120.a | L3/L4 | R1 | co-land |
| H15 | supervisor escalation reboot attributed (code 5), fed once before it (OR130) | A.U26.28, A.U31.07; OR130.a, G1/R20 | L4 | R1 | co-land (a code 2 is an OR130 failure, A.C.01 (9)) |
| H16 | recovery rungs on silicon (supervisor restart, participant rungs, bus clear, controller re-init, boot clear, WiFi radio re-init) | A.U26.34, A.U13.R02, A.U15.R01-R04, A.U16.R01, A.U16.R02, A.U16.R03 (`fram_cs_hijack_fault_injection_and_recovery.py` gains 'CS held inactive across two block writes'), A.U18.R01; G1/R20, G4/R22, OR113.a | L3/L4 | R1 | co-land |
| H17 | manual rungs: SCD30 and FRAM unplug/replug, SDA-to-GND | A.U26.34 (2); LEAD/R29 | manual | R2 | own step |
| H18 | held SDA vs MCU reset; SCL/SDA during `recover()` and the boot clear (scope) | A.U14.17 row, SUPP_recovery A.U13.R02 row | L3 + scope | R1 (L3 case), R2 (scope, if provided) | co-land + own |
| H19 | trigger spacing over a long run | A.U26.41 (2); G1/R30, G5/R07, G4/R64 | L4 `soak_duration` long | R5 | co-land |
| H20 | loop lag under combined load (flash script) and idle loop share | A.U31.06 (3), A.U8.11; G4/R64 | L3 | R1 | co-land + own figure |
| H21 | no-yield stretches; flash-write loop gap | A.U31.05; G4/R64 | L3; second script `persistence_write` | R1, R3 | co-land |
| H22 | FRAM command hold under the UART poll floor (BACKLOG T4) | A.U16.07, A.U33.07; G4/R64 | L3 | R1 | co-land |
| H23 | C-stack peak reading | A.U30.18; LEAD/R06 | L3 | R1 | co-land |
| H24 | alarm-pool `constructed=N` | A.U14.13 | L3 | R1 | own record |
| H25 | conformance probes SCD30, SGP40, BMP3xx (calibration block), FRAM, ISL29125 (12-bit cycle); SGP40 serial word 0 recorded | A.U26.66, A.U15.13; G7/R04 | L3 | R1 | co-land |
| H26 | register volatility (BMP3xx soft-reset key; ISL probe A03-A05); bench SCD30 NVM state recorded | G1/R04, G3.076 | L3 | R1 | own (A.C.16) |
| H27 | ISL29125 M.1.2 rows re-measured, PRST unit asserted (at HEAD), CONFIG1 restart reported | G3/R46 | L3; S3b gated | R1, R3 | own (A.C.19) |
| H28 | S3b envelope with `Overrange`; M1 rig geometry first | A.U26.11, A.U26.42 (3); G3/R54, G1/R40 | L3 `neopixel_sweep` + `persistence_write`; manual | R2 (M1), R3 (S3b) | co-land |
| H29 | lone-BMP3xx general call; non-SGP40 ACK/NAK of a broadcast | A.U35.21, A.U25.01 row | L3 | R1 | co-land |
| H30 | SCD30 wrong argument CRC / interval 0 reaction; 0x0010 readback across a power cycle | G7/R03 RF094, A.U25.01, A.U25.12, A.U15.08 | L3 `persistence_write` + `scd30_extra_write`; manual | R3, R2 | own (A.C.15) |
| H31 | SCD30 prerequisite start at most once; dependents by default; read-while-write gated | A.U26.07, A.U26.08, A.U26.09 | L3 | R1, R3 | co-land |
| H32 | SCD30 config-write arm under API load | A.U26.32; G1/R17 | L4 `persistence_write` + `scd30_extra_write` | R3 | co-land |
| H33 | Altitude with `AmbPres` 0 | A.U26.72; G7/R41, OR100.a | L4 both SCD30 flags | R3 | co-land |
| H34 | FRC readiness defaults measured | A.U26.84; REF/R06 | L4 `soak_duration` | R5 | co-land |
| H35 | lost SGP40 samples | A.U15.20 | L3 `soak_duration` short | R5 | co-land |
| H36 | `TempOffs` 0.53 stored as typed | A.U15.07 | L4 both SCD30 flags, optional | R3 | own (conditional) |
| H37 | UART hazards across the jumper and under load; multi-chunk SET; both CRC modes over the jumper | A.U26.82, A.U26.87, A.U26.33, A.S0930.05; LEAD/R28, LEAD/R31 | L3/L4 | R1 | co-land |
| H38 | CRC16 bench run on a reflashed image | A.S0930.06; OR116.a, OR118.a (4), OR123.a | L4 `flash_cycle` | R4 | co-land |
| H39 | lwIP stall reproduced on the unpatched image, then the override hammer | A.U21.14, A.U26.85; OR112, OR114.a (5), OR115.a (4), G4/R44 | L4 `flash_cycle`; default | R4 (pair), R1 (override half) | co-land |
| H40 | raised PCB count at the connection ceiling | G4/R44; A.U26.85 (2), `bench/test_network_resilience.py:1004` | L4 | R1 | co-land |
| H41 | body-cap binding (L32) | G6/R52, G4/R44 | L4 | R1 | own (A.C.13) |
| H42 | console output with a non-reading USB host, `DebugLevel` 0 | A.U19.23; G6/R52 D4.219 | L4 `persistence_write` (2 writes) | R3 | own step |
| H43 | caught allocation failure prints `memory allocation failed`; hardware gates turn red | A.U20.04, A.U35.05 (3) | L3/L4, throwaway worktree | R1 (end) | own (A.C.18) |
| H44 | heap bounds and post-build free heap on a named image; survivors incl. the VOC algorithm | G4/R47, A.U26.48, A.U30.04, A.U19.13 | L3/L4 | R1 | own record |
| H45 | two-image GC proof | G4/R49, OR40.a (3), G1/R02; A.U8.06 (UART tunables on both) | L3/L4, 2 planned flashes | R7 | own (A.C.09) |
| H46 | `ResetErrors` bench budget (BACKLOG items 24/32, R2 curve) | G4/R62, G5/R23; A.U11.31, A.U19.14 | L4 | R1 | own record → A.C.10 |
| H47 | config float round trip on silicon | A.U11.21; G5/R34 RF207, G5/R45 RF216 | L3 `persistence_write` | R3 | co-land |
| H48 | float boundary 2**24 and the bus-deinit no-op script on silicon | `float_boundary_2pow24.py`, `bus_deinit_is_a_noop_on_real_hardware.py`; G5/R45, G4/R19 | L3 | R1 | co-land |
| H49 | power cut during a config write | G5/R35, A.S0930.25 | manual, budgeted scratch writes | R2 | own (A.C.17) |
| H50 | forced config repair at boot; littlefs erase count per commit | A.U31.03 | L3 `persistence_write` | R3 | own step |
| H51 | malformed country code at the radio | G6/R28 RF213 | L3 | R1 | own (A.C.14) |
| H52 | `HotspotPW` PUT rows | A.U18.38 | L4 `persistence_write` | R3 | co-land |
| H53 | per-second `rssi` read cost | A.U18.33 | L3 | R1 | own record |
| H54 | request-head size of real browsers | A.U19.07 (`web.max_head_bytes`) | L4 capture, manual | R2 | own step |
| H55 | l3/l4/web tunables still "estimated": `outer_cap_s`, `per_call_timeout_s`, floors, `l4.dut_serving_after_sta_s`, `l4.lwip_spin_concurrent_request_max_s`, `l4.soak_request_failure_rate`, `boot.unfed_stretch_*` | A.U8.04, A.U8.11, A.U9.04, A.U10.07, A.U10.13, A.U21.14, A.U26.35, A.U26.41 (3), A.U26.54, A.U35.56 | L3/L4 | R1, R4, R5 | own record → A.C.10 |
| H56 | speed-probe bands; `tool.*` step timings; the lwIP host hammer's slowest write | A.U8.16, A.U35.23, A.U21.17, A.U21.13 | host | R0 | own |
| H57 | bench Pi: OS record, sudo/`--preserve-env`/`nmcli edit`/picotool checks, uv pin, stale packages | OR50.a (3)(b); A.U21.18, A.U21.19, A.U21.26, A.U21.27, A.U28.02 | host | R0 | own |
| H58 | `env --tier bench` with the installer's recovery timer; Playwright `install-deps` fatal | A.U21.23; U28 installer row | host | R0 | own |
| H59 | GCC ≥ 14 mbedtls build without the suppression (if no trixie chroot built it) | A.U21.16 step 1, A.SDEP.12 | host | R0 | own (conditional) |
| H60 | firmware pin moved: flash, bench, mid-soak on the new pin; F.5 on-target confirmations; `sys.implementation` | A.SDEP.08 (6), A.SDEP.25, A.SDEP.07 (a re-vendored freezefs changes the frozen website on silicon: the served site checked in the same runs); OR129.a (5) | L3/L4 | R1, R5 (on the pin the tree carries) | co-land (only if the pin moved) |
| H61 | spoofing tests; the off-subnet attempt | A.U26.56; G8/R40, OR77/OR79 | L4 | R1 | co-land + own verdict |
| H62 | role reversal, destructive stage last; `_PHASE_DEACTIVATED` cleared by `machine.reset()` | A.U26.39; G1/R28 | L4 `persistence_write` | R3 | co-land |
| H63 | rollover over ~12.4 days | A.U26.36; G1/R23 | L4 `multi_day_rollover` | R6 | co-land |
| H64 | 6 h soak (S4), liveness, failure rate | A.U26.35; G1/R22 | L4 `soak_duration` long | R5 | co-land |
| H65 | bench facts: I2C scan per bus (MPRLS on i2c0?), FRAM RDID, rig geometry, DHCP keying, BME688, host OS and stale packages | A.U26.46, A.U26.42, A.U1.04; G1/R40 | L3, manual, host | R0, R1, R2 | own record |
| H66 | Safari/mobile pass; captive-portal webview | G7/R32; A.U26.42 (4) | manual | R2 | own step |
| H67 | the neu units and `arzi` against their TOMLs (physical check, no flashing) | G8/R18 | owner, physical | R2 | own step |
| H68 | torn-write expectation on the bench reset race | A.U35.40 | L4 `persistence_write` | R3 | co-land |
| H69 | watchdog-starvation flash test ends on a serving board (BACKLOG "Not yet confirmed" (2)) | A.U26.25, A.U26.17; HW.S28 | L3 | R1 | co-land |
| H70 | reflash smoke test (exit-249 retry only); toolchain re-verification | A.U26.14 | L3 `flash_cycle`, `toolchain_reverify` | R4 | co-land |
| H71 | silicon-only interaction, recombination and rung cells of B3 | A.U35.08, A.U35.09, A.U35.52, A.U35.54 (`audit/b3/queue_c.md`) | L3/L4 | R1 | co-land |
| H72 | FRAM-only forensic scripts clear their chunk; reset-race seams | A.U26.22 (5), A.U26.43 | L3 | R1 | co-land |
| H73 | every other new or changed L3/L4 test, device script, fixture or tag: A.U0.18, A.U0.28, A.U0.35, A.U1.25, A.U2.01-A.U2.03, A.U4.07, A.U6.17, A.U7.13-A.U7.17, A.U7.24, A.U8.04-A.U8.08, A.U8.14, A.U8.19, A.U8C.01-A.U8C.121 and A.U8C2.01-A.U8C2.51 (the `tests_hardware` ones), A.U10.34-A.U10.37, A.U10.40, A.U10.41, A.U11.33, A.U15.15, A.U17.05, A.U18.42, A.U20.33, A.U21.24, A.U25.50, A.U25.61, A.U26.04-A.U26.87 not named above, A.U27.19, A.U27.25, A.U27.29, A.U27.37, A.U28.27, A.U28.28, A.U28.35, A.U29.04, A.U30.14, A.U30.16, A.U31.01, A.U31.04, A.U35.03, A.U35.22, A.U35.49, A.U35.50, A.U12.18 (`device_scripts/sgp40_same_device_concurrent_sessions.py`, its `flash/test_bus_concurrency.py` leg and L4 case), A.U18.01 (the AAAA query in `bench/test_hotspot_role_reversal.py`) | as listed | default/gated per marker | R1 (default), R3 (gated) | co-land |
| H74 | twin corrected until it agrees; fidelity rows; BACKLOG owed rows removed as delivered; Part N measured | OR17.a (5), G6/R56, G7/R03, G9/R31, A.U25.01 | — | after each | own (A.C.10) |
| H75 | F17 (BACKLOG item 44): no unexplained reset across the rounds | G1/R02, G4/R63 | — | R7 | own (A.C.09) |
| H76 | UART `wrnno` 11 against a real babbling peer (BACKLOG R13 + N3) | BACKLOG owed row | — | none | stays owed: "needs hardware the bench does not have" (owner, 2026-09-25) |
| H77 | FRAM CS level at power-up on each board | G5/R29 State (and G3/R16 before wave 2) | — | none | withdrawn by the lead (AC_NOTES 11, 23): hold time met by boot timing, a documented datasheet fact; register fix 1 |
| H78 | SGP40 wrnno 35 (today `W13`) spends one slot per NTP outage: UDP 123 blocked past `SGPWaitTimeNTP`, one entry per outage, `ErrCount` rising per backup (zero wear) | BACKLOG `:362-364` 'Not yet confirmed on silicon' (1); A.U2.13 | L4 (bench `iptables` fault, switch armed) | R1 | own step |
| H79 | worst-case read duration per driver for `stagger.min_read_separation_ms` | A.U10.13 | L3/L4 | R1 | own record |
| H80 | LED ramp wall time under bench API load for `_MAX_SIGNAL_S` | A.U9.04 | L4 | R1 | own record |
| H81 | recovery-ladder thresholds (participant 2nd, bus clear 3rd, controller 4th failure; FRAM probe 2nd; three identification attempts) confirmed from the rung tests | SUPP_recovery closing note (`:923-925`) | L3 | R1 | own record |
| H82 | `stations` query without the 100 ms settle keeps the right count (local-only image, reverted at once) | A.U18.43, A.SDEP.17 (W42) | L4, `flash_cycle` (2 flashes) | R4 | own step |
| H83 | loaded free-heap floor from `MemFree` under the bench load | A.U30.09 | L4 | R1 | own record |

## Ledger
| register block | clause for this unit (short) | result |
|---|---|---|
| G1/R02 | hardware in C — the rounds: evidence first, image proof, lower levels first, default before gated, plan per round, twin corrected, two-image proof, boot log, trigger timestamps, `reset_reason` codes, stale packages, F17 closure | A.C.01 (frame), A.C.02-A.C.09 (rounds), A.C.10 (twin/doc deltas), A.C.11 (close); inventory H01-H07, H45, H57, H75 |
| G1/R04 | hardware in C — re-read bench NVM state and register volatility (G3.076) | A.C.16 (soft-reset discriminator for BMP3xx; ISL probe keys A03-A05; SCD30 NVM state recorded), A.C.03 (1) (first-contact `/sensors`) |
| G1/R14 | hardware in C — each code | A.U26.28 (codes 1-6, co-land, R1/R2), A.S0930.29/.40 (7, 8, 3, 4), A.C.12 (0, 9, 10+p, 20); register fix 3 |
| G1/R20 | hardware in C — the runs (each rung on silicon, discriminating oracle) | A.C.03 (A.U26.34 automated, A.U13.R02, A.U26.28 code 5), A.C.04 (manual rungs); H15-H18 |
| G1/R22 | hardware in C — S4 (the 6 h run, release evidence) | A.C.07 (`--soak-duration long`, A.U26.35's rate measured); H64 |
| G1/R23 | hardware in C — the rollover run | A.C.08 (A.U26.36); H63 |
| G1/R28 | hardware in C — confirm `machine.reset()` clears `_PHASE_DEACTIVATED` | A.C.05 (1) (A.U26.39 (3)-(4) stage 8 check, gated); H62 |
| G1/R30 | hardware in C — bench boot log and trigger timestamps | A.C.01 (8)/A.C.03 (boot log every round, A.U26.41 (1)), A.C.07 (trigger spacing, A.U26.41 (2)); H06, H19 |
| G1/R40 | hardware in C — rig geometry (M1), i2c0 scan; owner confirms DHCP keying and BME688 at the first round | A.C.02 (7) (owner confirmations), A.C.04 (1) (M1), A.C.03 (sweep's `ADDRESSES` lines, A.U26.46 table); H65 |
| G3/R46 | hardware in C — undocumented ISL29125 behaviour measured, dated, specimen count; PRST unit asserted; restart reported | A.C.19 (the PRST assertion holds at HEAD, `isl29125_real_irq_edge.py:117-121`; A.C.19 re-measures the M.1.2 rows and corrects the stale host comment) |
| G3/R54 | hardware in C (S3b) | A.C.05 (3) (A.U26.11 gated S3b, M1 first in A.C.04); H28 |
| G4/R19 | hardware in C — `bus_deinit_is_a_noop_on_real_hardware.py` kept as a pin-move check | A.C.03 (runs in R1's default flash tier), A.SDEP.08 (6) on a pin move; H48/H60 |
| G4/R22 | hardware in C — one row measures a held slave vs reset; boot-time bus clear; ladder rungs | A.C.03 (A.U13.R02 incl. the boot clear with SDA held, co-land), A.C.04 (5) (scope rows if a scope is provided, else they stay owed); H16, H18 |
| G4/R44 | hardware in C — stall reproduced on HEAD firmware, then the override; raised PCB count and body-cap binding (L32) | A.C.06 (1) (A.U21.14/A.U26.85 pair), A.C.03 (override half, ceiling tests), A.C.13 (L32 binding); H39-H41; register fix 4 |
| G4/R47 | hardware in C — `_MAX_USED`/`_MAX_ROUTE_NEED` re-derived on a named image | A.C.03 (4) (figures recorded with the image), A.C.10 (re-derivation only as a new derivation of the need); H44 |
| G4/R49 | hardware in C — two-image proof | A.C.09 (1)-(2); H45 |
| G4/R62 | hardware in C — bench budget (`error_log_helpers.py`) | A.C.03 (4) (measured after the evidence save), A.C.10 (tagged budget constant; BACKLOG item 32 closes); H46 |
| G4/R64 | hardware in C — loop-lag and trigger timestamps on the bench; FRAM hold script | A.C.03 (A.U31.06 (3), A.U31.05, A.U16.07), A.C.07 (trigger spacing); H19-H22 |
| G5/R03 | hardware in C (each code on silicon) | as G1/R14: A.U26.28, A.S0930.29/.40, A.C.12 |
| G5/R05 | hardware in C — bench boot log | A.C.03 (A.U26.41 (1)); every round's record (A.C.01 (8)) |
| G5/R07 | hardware in C — trigger timestamps | A.C.07 (A.U26.41 (2), long duration); H19 |
| G5/R23 | hardware in C — bench budget | as G4/R62: A.C.03 (4), A.C.10 |
| G5/R29 | hardware in C — CS level at power-up on each board | NO-CLAUSE after the lead's withdrawal (AC_NOTES 11, 23; end of `U13.md`): the hold time is met by boot timing, a documented datasheet fact; H77; register fix 1 |
| G5/R34 | hardware in C — round trip on silicon (RF207) | A.C.05 (1) (A.U11.21's gated L3 test); H47 |
| G5/R35 | hardware in C — power-loss window and littlefs repair (G5.035) | A.C.17 (operator power cut during scratch writes through the product path), run in A.C.04 (4); H49 |
| G5/R45 | hardware in C — float device scripts; config round trip by an L3 device script (RF216) | A.C.03 (`float_boundary_2pow24.py`), A.C.05 (A.U11.21); H47, H48 |
| G6/R28 | hardware in C — what the radio firmware does with a malformed country code (RF213) | A.C.14 (new instrument: A.U26.20 deletes the only script that called `network.country()` directly); register fix 2 |
| G6/R52 | C (L32 binding at L4); hardware in C — console output cannot starve the watchdog with a non-reading CDC host | A.C.13 (binding), A.C.05 (1) (A.U19.23's hardware row, `DebugLevel` 0, gated for its 2 writes); H41, H42 |
| G6/R56 | hardware in C (G6.032 fidelity rows; RF100 CONFIG1 restart assumption row) | A.C.10 (rows updated from the rounds), A.C.19 (CONFIG1 restart facts reported, row stays an assumption unless settled), A.C.15/A.C.16 (SCD30, BMP3xx rows); H74 |
| G7/R03 | hardware in C (assumption rows) | A.C.15 (SCD30 argument reaction; 0x0010 across a power cycle), A.U35.21 (non-SGP40 broadcast NAK, co-land), A.U26.66 (BMP3xx calibration block), A.U26.28 (BOOTSEL round trip), A.C.19 (CONFIG1 restart); H25, H29, H30 |
| G7/R04 | hardware in C (run the probes; ISL29125 12-bit cycle measured) | A.C.03 (A.U26.66's gate, co-land), A.C.16 (BMP3xx reset key); H25 |
| G7/R07 | hardware in C (each code on the dev bench) | as G1/R14; the survive/clear rules on silicon read from codes 1-6 and 0 (A.C.12 (1)) |
| G7/R32 | hardware in C (manual Safari/mobile) | A.C.04 (6) (browser pass, captive-portal webview through A.U26.42 (4)); H66 |
| G8/R18 | hardware in C — the three neu units and `arzi` against their TOMLs | A.C.04 (7) (owner's physical check; no unit but `dev` flashed or connected); H67 |
| G10/R24 | — | NO-CLAUSE: State "holds; work: doc in U36" names no C work; the block entered the input through the string "in C.10" (State) — register fix 6 |
| LEAD/R27 | applies to every phase-C round (rare events triggered or recorded; dedicated repro scripts) | A.C.01 (9) (A.U26.81's README paragraph is the permanent text) |
| G8/R40 | hardware in C — the off-subnet spoof attempt; the skip reason rewritten after it | A.C.03 (3) (A.U26.56 (3)); H61 |
| LEAD/R02 | hardware in C (start and end state every round) | A.C.01 (6), (8) (A.U26.79's fixtures run every round), A.C.09 (release image at the end); H05 |
| LEAD/R06 | hardware in C (measurement) | A.C.03 (A.U30.18's device script, R1 default flash tier); H23 |

## Register fixes
1. **G5/R29** State: "hardware in C — CS level at power-up on each board" → delete; append "CS pad state during reset and
   the power-on hold time (met by boot timing) are a documented datasheet fact in SPEC C.3.1 (lead, 2026-09-29, AC_NOTES
   11, 23); no phase C row". Evidence: the lead's note at the end of `audit/actions/U13.md` and AC_NOTES item 23
   (G3/R16's same item dropped in wave 2, `REGISTER_FIXES_wave2.md:62-66`, which left the C row to "A-C's rewrite of
   A.U13.04").
2. **G6/R28** State, after "the C row measures what the radio firmware does": append "— instrument: a flash-tier device
   script calling `network.country()` with malformed values (A.C.14); A.U26.20 deletes `wifi_country_hostname_edge_values.py`,
   whose only country case used MicroPython's own default `XX` (N.53)".
3. **G1/R14 / G5/R03 / G7/R07** State: add "codes 0, 9, 10+p and 20 are attempted on the bench by device scripts that
   write region 0, rebind a step or recurse from outside (A.C.12, harmonization 45); a code the attempt cannot reach is an
   E.6 exception with the attempt's result" — A.U26.28's "boot-failure … listed as a structural exception" is no longer
   the plan.
4. **G4/R44** State "hardware in C — raised PCB count and body-cap binding (L32)" → name the instruments: "raised PCB
   count: the ceiling tests and A.U26.85 (2) at L4; binding: an oversized `Content-Length` answered 413 before any body
   byte is sent (A.C.13)"; and the premise in `SPECIFICATION.md:5238-5243` ("a socket cannot distinguish 'buffered then
   rejected' from 'rejected unread'") is wrong: a 413 arriving before the body is sent can only come from a body never
   read (`ext/microdot.py:425-430, 1443-1445`); the SPEC sentence is rewritten with the silicon result (A.C.10).
5. **G1/R04** State: "hardware in C — re-read bench NVM state and register volatility" → add "volatility checked with
   each chip's reset command (a volatile register returns to its datasheet default; an NVM-backed setting survives, as
   SCD30's do), power-on reset per BMP384 `ds003:401, 899-903` (the dev board's part), as BMP388 `ds001:454, 1717-1718`,
   and ISL29125 `:411-415` (A.C.16)".
6. **Input generator** (`audit/sweeps/al_input.py:10`): `C_RE` matched G10/R24's State 'stated once in C.10' (SPEC Part
   C, not unit C) and missed 'phase-C' (LEAD/R27, G8/R40). Replace with
   `r"(?i)\bphase[- ]C\b|hardware in C\b|\bin C\b(?!\.\d)|\bC —"`.

## Open points
None. Every choice was settled by an owner row, the register or a CLAUDE.md rule: the network switch around every
bench-tier run follows CLAUDE.md's "tearing down `br0`/its slaves" literally (A.C.01 (2)); the lwIP pair order is
OR114.a (5)'s, kept inside one round, with G1/R02's gated-after-clean rule (A.C.06); local-only control and no-threshold
images are throwaway-worktree builds, as A.U21.14 and G1/R02 ("a local-only image is reverted at once") state
(A.C.06, A.C.09), the control image's path passed to A.U26.85's test by a host option (A.C.06 (1), A-C note 1); scope rows run only if the owner provides a scope, else stay owed (A.C.04 (5)).

## A-C notes
1. The control-image conflict is settled in C (A.C.06 (1)): the round builds the control image before the run in a
   throwaway worktree of its commit with the override call removed (A.U21.14's form, never committed; its image record
   carries `overrides: []` and `dirty: true`) and passes its path to A.U26.85's test through a new host option
   `--lwip-control-image <path>`; the test refuses (fails, never skips) a missing path or a record whose `overrides` is
   not empty, and in `finally` reflashes the release image recorded at start. A.U26.85 (1)'s 'the test itself builds the
   control image' becomes 'the test takes the control image the round built'. No build flag is added. Co-lands with
   A.U26.85 and A.U21.14 — A-C merges.
2. A.C.12 replaces A.U26.28's boot-failure exception row; A.C.13 adds a `_JUSTIFIED_UNMARKED` reason to A.U26.06's guard
   file; A.C.15 (1) and A.C.05's A.U15.07/A.U19.23 rows add budget rows to A.U26.09's README table; A.C.16 extends A.U26.66's
   BMP3xx probe; A.C.19 edits the comment at `flash/test_bus_concurrency.py:95-97`, which U8C tag actions also touch — all co-land with U26 in the B2 order.
3. A.C.14's script and A.C.12's scripts join A.U26.05's twin-runner record and A.U35.49's review (`audit/b3/queue_c.md`,
   A.U35.54, lists every C row: U37's A.U37.05 folds both lists into BACKLOG).

Verified 2026-09-30 (`audit/actions/verify/C.md`): V.C.01-V.C.20 applied.
