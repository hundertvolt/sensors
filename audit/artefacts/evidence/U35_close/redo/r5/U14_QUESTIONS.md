# U14: the agents' decisions, compiled into owner questions (read-only, 2026-11-06)

Integration head f509c906. Material: `git grep -n "(agent, 20" -- ':!audit' ':!arduino' ':!legacy' ':!python'`, 466
lines, each read in its paragraph or code. Sorted: **269 choices, 197 records**. A record had no real alternative (a
datasheet or source fact, a measurement, an owner ruling it follows, the 17 owner-reviewed lines among them, or
wording); `U14_TAGS.tsv` names the citation replacing each record's tag. The choices form 15 realms, merged into **11
questions** (owner, 06:56: 20 a soft target). Each question covers every choice of its realms, light ones included.

## Realm map
| Realm | Choice lines | Record lines | Asked in |
|---|---|---|---|
| Project rules (principles, process) | 5 | 13 | Q1 |
| Recovery, reset reasons, watchdog | 13 | 4 | Q2 |
| Logging and error codes | 3 | 6 | Q2 |
| UART link | 21 | 14 | Q3 |
| Test tiers and test rules | 79 | 43 | Q4 |
| Digital twin fidelity | 32 | 15 | Q5 |
| Provisional numbers (Part N estimates) | 34 | 3 | Q6 |
| Memory | 5 | 9 | Q7 |
| Storage (FRAM, config files) | 3 | 8 | Q7 |
| Sensors | 10 | 14 | Q8 |
| Network services (Wi-Fi, NTP, DNS; every Wi-Fi line a record, owner 2026-10-28 08:57) | 5 | 20 | Q9 |
| What the unit exposes on the network | 3 | 3 | Q9 |
| Web server and website | 10 | 16 | Q10 |
| Code conventions | 19 | 7 | Q11 |
| Build chain, CI, bench host | 27 | 22 | Q11 |
| **Total** | **269** | **197** | 11 questions |

## Q1. The project rules the agents wrote down (5 choices)
**Big picture.** The owner's pillars P1-P6 and "nothing proven good shall be removed" are the base. The agents added
five pillars, each restating a rule in force (P7 one source of truth, P8 wear nothing a test does not own, P9 cite and
date, P10 one contract per interface the project cannot change alone, P11 a workaround names what retires it).
**Weightiest choices.**
- "Proven good" means: it fixes or prevents an observed or reproduced failure, measurably improves the device or the
  build, or the owner approved it. This decides what any cleanup may remove.
- A case no rule covers is decided by the product concept (the owner's "runs indefinitely ... handles all issues").
- Every input that arrives untyped is checked where it enters: REST bodies, device TOML fields at build time, and
  state read back from FRAM or the flash file system.
**Where another ruling changes something.** A narrower "proven good" (observed failures only) lets a cleanup remove
measured improvements or owner-approved code; a wider one (anything with a test) keeps more code. Trusting stored
state on read saves checks but trusts storage that a power loss can tear.
**Recommendation.** Accept as is.

## Q2. What the unit records, and does, when something fails (16 choices: recovery 13, logging 3)
**Big picture.** A fault is retried, then the module reset, then its task restarted, then the unit rebooted, with
the hardware watchdog as last net (the owner's ladder); every reboot leaves a reset code the next boot reads. The
agents decided how codes are written around system commands and a dying event loop, where the watchdog is trusted
instead of a second mechanism, and which situations log an error at all.
**Weightiest choices.**
- A system command (reboot, config reset, FRAM erase) writes "command incomplete" (code 9) before its shutdown steps:
  a hang, a failed delete or a lost config reads 9 at the next boot, never an HTTP "Failed" (the reply goes out when
  the command is accepted, before the reboot).
- A reset timer fire the scheduler drops is left to the watchdog, and the record decodes it as the intended reset.
- When the event loop itself ends, a reset already underway keeps its record; during boot nothing is written.
- ResetErrors is also refused after a fault of the supervisor itself (the owner's "2 b" extended to that case).
- The supervisor's 2 s scan is held to "x 4 within the 8 s watchdog", a reading of upstream's "keep << timeout".
- The hotspot's DNS server task lives outside the task supervisor, coming and going with the hotspot mode.
- An expected situation never logs an error code, only a console line (generalised from the owner's "startup jitter
  logs nothing"); a repeat during `ResetErrors` takes a new slot only if the log is really cleared; DNSSRV logs apart.
**Where another ruling changes something.** A reply after the steps cannot reach the client (the reboot cuts it); a
second path for a dropped fire adds code the watchdog makes needless; warnings for expected situations would fill
each module's 10-slot FRAM history with normal events and push real faults out.
**Recommendation.** Accept as is. The real margins behind the watchdog choices are unmeasured: see Q6.

## Q3. The UART link, and how its hazards are proven under load (21 choices)
**Big picture.** The UART link is a bench-only module on `dev`. It never blocks the loop: it reads only what has
arrived, polls fast inside a transaction and slowly while idle. To meet "system shall be proven stable unter max load
allover" (owner, 2026-10-21), the agents built the proof into dev's link exerciser.
**Weightiest choices.**
- Hazard mode: `PUT /status` with `UartHazards` on dev runs one bounded hazard run (two initiations at once, both ends
  transmitting, the first-chunk field sweep) while readers hammer `/status`, then the echo resumes; never persisted,
  never at boot. Decided "on the owner's behalf for review".
- Two hazards stay outside it (a stalled transmit, `clear()` racing a transaction), run on the flash tier with
  `main.py` stopped. One run fills the responder's 10-entry FRAM log, so the website warns first.
- An idle listener polls at a second, slower rate (50 ms against 2 ms): the owner's never-block rule extended to a
  wait that never stops working (measured 1,244 against 60 poll rounds in 3 s).
- Every hazard check runs in both CRC modes; a stored train is answered piece by piece, not as one large copy;
  `ResetErrors` never re-arms the "no valid frame since boot" diagnostic.
**Where another ruling changes something.** A bench-only image keeps hazard code out of dev's, but then the proof no
longer runs on the shipped image; the two left-out hazards need the driver to keep port and pins across a re-init.
**Recommendation.** Accept as is: the mode lives only in dev's bench module, which no other device carries.

## Q4. What the real board never proves, and the rules every test follows (79 choices)
**Big picture.** Every behaviour is tested on the PC tiers (mock, twin); the flash and bench tiers repeat it on the
board unless SPECIFICATION.md E.6.6 records an exception. For nine behaviours the agents left the board test
unwritten. About 66 of the 79 lines are test-local details, which stay in their tests (owner, 2026-11-04).
**Weightiest choices.**
- Eight rows read "a gap until written" (each reachable from a device script, none written): a held SDA during the
  full system's boot; a system command in the boot window; failed timer arms beside the running system; an RTC step
  under it; `main()` ending or raising inside it; the UART config flush during link traffic under API load; two
  webserver refusals over bench HTTP; each reader's floor after saturation. A ninth, NTP failure modes, needs a
  scriptable NTP server the bench lacks.
- "Months of uptime" is proven per device by a driven-clock scenario (forty simulated days), not a wall-clock soak.
- A soak proves only liveness; a leak claim needs a rate bound. Waits poll for their state, with a deadline.
**Where another ruling changes something.** Writing the scripts proves firmware recovery paths on silicon (one device
script and some bench time each, no firmware change); a months-long wall-clock soak is not practical at all.
**Recommendation.** Write the four that prove firmware recovery paths (command in the boot window, failed arms beside
the system, `main()` ending inside it, held SDA at full boot) in the last hardware round; record the other five as
accepted limitations; accept the test rules. SWEEP.md's findings 9 and 10 on the same table are asked apart.

## Q5. Where the digital twin is simpler than the board (32 choices)
**Big picture.** The twin runs the real firmware on the PC against fake chips and a fake radio, without electrical
behaviour, bus and conversion timing, radio faults or a real network stack, each covered on silicon. The 2026-10-28
conformance probes found five fake answers that differ from the bench's chip, all "accepted until corrected".
**Weightiest choices.**
- SGP40: the fake returns a new random serial number on every read; the real chip's is fixed.
- BMP3xx: the fake keeps the data-ready bits set after a data read (the chip clears them), so in the twin the
  driver's status poll always reads "ready"; it shows power-control 0x00 where the chip shows 0x13, then 0x03.
- BMP3xx oversampling after a soft reset: bench part 0x00, both datasheets 0x02; neither side moves until re-read.
- SCD30: a read with no command pending gives zeros in the twin, 0xDD on the chip; no driver path makes that read.
- Runtime: soft timer callbacks never queue or drop in the twin (a flash script covers it); the watchdog is a task.
**Where another ruling changes something.** Correcting the fakes where datasheet and chip agree (SGP40 serial, BMP3xx
data-ready and power-control; the bench asked on 2026-11-05) makes twin runs exercise the driver's real data-ready
wait. Test side only, no firmware change; a few twin assertions may need adapting.
**Recommendation.** Correct those three fakes; accept the rest as they stand.

## Q6. Numbers that are estimates, not measurements (34 choices)
**Big picture.** Every tuned value has a Part N row. For 34 the agents set an estimate, "measurement owed", in the
firmware, website, test tiers and CI; three read "unknown until measured", and all three bound the watchdog.
**Weightiest choices.**
- Unknown until measured: the boot's two unfed watchdog stretches (boot entry to the first setup feed; last setup
  feed through task start, timers and the first NTP sync) and one supervisor pass with every task dead, against 8 s.
- The recovery ladder's counts: device reset after 2 failed read cycles, bus clear after 3, controller rebuild after
  4 (the order is the owner's, the counts estimates).
- Firmware: request head limits (32 header lines, 2,048 B), LED signal wait 120 s, I2C timeout ceiling 200 ms,
  emergency exception buffer 100 B, UART polling 2 ms in a transaction.
- Website: retry backoff capped at 60 s, a device check every 60 s, "clock mismatch" beyond 5 s.
- Tests and CI: the serving-demand budget (72,232 B), soak failure share 0.001, flash-script budgets, CI probe and
  apt timeouts, the least read spacing a test accepts (100 ms).
**Where another ruling changes something.** Measuring the firmware values in the last hardware round may expose a
too-small margin, meaning a firmware change after round 1's "final" image. Leaving all owed costs nothing now.
**Recommendation.** Put the three watchdog-margin measurements in the last round (the boot stretches are already owed
at BACKLOG.md:151; the scan has no BACKLOG entry yet); leave the other 31 provisional with their measurement owed.

## Q7. Memory and stored data (8 choices: memory 5, storage 3)
**Big picture.** There is no free-heap floor (the owner retired them, 2026-09-19); instead the worst concurrent
serving demand at the connection ceiling must still find room, each budget re-read from the build. Buffers that would
churn are kept; buffers used rarely are built per use. The FRAM write order and checks are owner-agreed records.
**Weightiest choices.**
- Serving demand per connection: a head up to 2,048 B, a body up to the content cap, the largest GET body and the
  chunk buffer; the connection ceiling must place that many at once.
- One 32-byte scratch per I2C bus, kept for life; one FRAM buffer per chunk operation, built and dropped.
- A saving of about 1,700 B per FRAM chunk operation was declined so the error log call stays at its decision.
- A config file damaged from outside after boot is silently repaired from the in-memory copy at the next write (the
  unit is its only writer; damage found at boot is reported in `ConfigFaults`). A blank FRAM block reads unmarked.
**Where another ruling changes something.** Taking the 1,700 B saving moves logging off its decision site (C.7.1).
Reporting outside damage after boot needs a read before every write, for a case only a person with a cable causes.
**Recommendation.** Accept as is.

## Q8. Sensor details where the datasheet is silent (10 choices)
**Big picture.** Drivers follow their datasheets; where one is silent, or the owner set only criteria, agents chose.
**Weightiest choices.**
- BMP3xx: the command-ready wait is bounded at 50 ms (no datasheet bound), so a bus fault cannot hold a read.
- SCD30: with a stuck data-ready pin the reader falls back after twice the measurement interval; forced-recalibration
  readiness uses running sums and a temperature-change guard (the agents' reading of the owner's FRC criteria).
- ISL29125: the auto-range rule, generalised from two owner rulings (owner, 2026-09-26: "open to change"); the
  calibration band, windows and hold times; an interrupt parked while green is outside the active window; the chip's
  config compared with its copy every read cycle, so a corrupted byte is re-applied on a unit nobody watches.
- RGB to XYZ uses the sRGB/D65 primaries as a documented placeholder (the datasheet says they are per setup).
**Where another ruling changes something.** Checking the ISL29125 config only after a failed write saves bus traffic,
but a byte corrupted on the bus stays wrong until the next settings change.
**Recommendation.** Accept as is; the calibration constants are Part N rows and stay open to change.

## Q9. Network services and what the unit answers on the network (8 choices: services 5, exposure 3)
**Big picture.** Wi-Fi behaviour is the owner's throughout ("I decided everything already"). What is left concerns
NTP, the hotspot's captive DNS server, input shapes, and which MicroPython network services stay on.
**Weightiest choices.**
- The "Time May Be Stale" flag in `/status` is null before the clock is set and true while NTP is not synced (the
  owner asked for the flag; its form was decided for review).
- An NTP reply is accepted only through the connected socket (resolved address and port), no further origin check.
- `Hostname` must be a valid host label and `Country` two capital letters, checked at PUT and at use.
- Under a datagram flood the captive DNS yields once per datagram; a heap failure while parsing is logged and pauses it.
- mDNS (the hostname announce), ICMP and IPv6 stay on as built; a new route or command joins the threat table at once.
**Where another ruling changes something.** Turning mDNS and IPv6 off in the build narrows what the unit answers and
loses `hostname.local`; a build-configuration change, not a C patch.
**Recommendation.** Accept as is.

## Q10. The web server and the website (10 choices)
**Big picture.** The server is vendored Microdot inside the project's limits; the website polls one section at a time.
**Weightiest choices.**
- Leaving a page section lets its in-flight GET finish and be discarded, since an abort makes the device log a peer
  reset on every click; the next section's first answer waits a median 217 ms instead of 7 ms (decided for review).
- lwIP's inbound buffer pool stays at the port default; a 2,000 B lwIP memory floor per connection.
- A per-request exception catch around Microdot is kept from field experience with it.
- The website shows two decimals by default, the lower of the owner's two examples ("2 or 3 digits").
- Status-code tables beside their descriptions; dimensionless values carry no unit; the inline page bootstrap is not
  type-checked; one catalog table is coloured on the page.
**Where another ruling changes something.** Three default decimals show one more digit on every value without its
own setting; aborting on a section switch trades the wait for a logged peer reset per click.
**Recommendation.** Accept as is.

## Q11. Accept the rest as they stand (46 choices: code conventions 19, build chain and CI 27)
**Code conventions.** Every function explains itself in `#` comments under its `def` (one docstring per module);
member order details; imports static at module top; configuration as named tuples; `ruff format` unused.
**Build chain and CI.** CI pinned to ubuntu-24.04; each job's time limit from measured runs plus 25 %; the CI apt
cache keeps Ubuntu's signature as its integrity anchor; the GCC 14 workaround goes once a GCC 14 build is clean;
versions bumped by hand; mpy-cross's `-X no-source-lines` unused (tracebacks keep line numbers, at some flash cost);
stub defects repaired, never silenced; import-linter, vulture, detect-secrets and codespell declined after a trial
run; flashing outside the build scheme; CI's `needs:` edges sequence jobs, never gate them.
**Recommendation.** Accept as they stand: none changes what the device does (the nearest, traceback line numbers).
