# The 68 significant and moderate decisions the owner answered on the A-C review page (2026-10-02)

Generated from `audit/review/decisions.json` and `audit/review/answers.json`: each decision as proposed, the owner's status (ok = fine, change, ask = question or addition) and their note verbatim, and the refs that locate it.

## release-version-2-0 [significant] status=ok
decision: The firmware and website ship as version 2.0: today's pre-release 2.0b0 without its beta marker. The tag on the final merge is v2.0.
refs: A.U37.11; M.GEN.021; M.DOCS.059; M.SPEC.150; M.PROC.044; LEAD/R15; OR5

## rest-key-scheme [significant] status=ok
decision: You decided on one key scheme, with the new API as the reference. The planning chose the spelling: setting and value keys in PascalCase, acronyms upper-case, the full words Interval and Offset, 'Pres' for pressure, and no unit in a REST key (the unit sits in the field's description). Examples: NTP_Host becomes NTPHost, NTP_Offset_S becomes NTPOffset, Interv becomes FlashInterval, SGPResetVOC becomes ResetVOC, ISLCalibrate becomes Calibrate, lightCmdLED becomes LightCmdLED with R/G/B/T, UtcTime becomes UTCTime. Envelope and section keys stay lowercase, measurement fields keep their names.
refs: A.U10.40; G10/R12; G10/R14; M.GEN.017; M.SRC_NET.043; OR58; OR58.a

## rest-api-frozen-at-release [significant] status=ok
decision: The REST API (routes, keys, types, units, ranges, result words) gets one reference generated from the code. The mock server, website tests, the twin's PUT matrix and the fifteen places that copy the route list by hand are checked against it or derive from it. From the release on, a stored copy of it fails a check on any unrecorded change, like the stored-config check you already asked for.
refs: LEAD/R08; OR58.a; OR52.a (2); M.GEN.018; M.SPEC.116

## website-unattended [significant] status=ok
decision: A page left open keeps its memory and timers bounded, updates read-only values in place instead of rebuilding the page every 3 seconds, and after a device reboot or reflash notices the changed build on its next check and reloads itself. The device check runs every 60 s; failed polls back off to at most 60 s.
refs: LEAD/R09; A.U23.05; A.U23.06; M.WEB.003; M.WEB.020; M.WEB.025

## website-accessibility [significant] status=ask
decision: Unique ids for every field (numbered by position), every label bound to its control, the closed menu drawer made inert with focus handled, AA contrast in both themes, password inputs styled like other inputs and marked autocomplete='new-password', reduced motion honoured. An automated check in the website tests proves it, written without a new npm dependency.
NOTE: Fine, and make the "back" function of the browser work. Currently, clicking through the menu / the pages leaves no history, and a "back" immediately exits to the website visited before ever opening the sensor page. I want "back" to move backwards through the sensor subpages openend through the menu as well (actually the most intuitive way)
refs: LEAD/R10; A.U23.40; A.U23.43; A.U23.44; M.WEB.014; OR132.a

## dns-fallback-clear-confirm [significant] status=ask
decision: The new Clear button for the DNS fallback servers asks the browser's own confirmation ('Clear DNS Fallback Servers?') before it sends the empty value. It is the only dialog on the site; the system commands, including Reset to defaults and Erase FRAM, keep none, as you decided.
NOTE: Fine, and add a dialog to all system commands and the clear error history as well. But only on the website, not on the API side. The API stays single command.
refs: A.U23.17; M.WEB.021; OR56.a (2); OR122.a (2)

## sgp40-wait-zero [significant] status=ok
decision: With WaitTimeNTP = 0 the SGP40 restores its VOC backup immediately at boot, without waiting for NTP, rather than never restoring it.
refs: G9/R03; HARVEST_REQUIREMENTS 3.3; OR57.a

## apply-failure-marks-fields [significant] status=ok
decision: When an Apply gets no per-field answer back (the request failed), every field it sent is shown as Failed on the page, instead of the failure only being logged.
refs: G7/R41; HARVEST_REQUIREMENTS 3.3; M.WEB.021; SPEC H.4

## c-stack-reboot [significant] status=ok
decision: A C-stack overflow caught anywhere is recorded, and the supervisor reboots the unit at its next pass with reset reason 20. The deepest await chain is measured and must stay at most half of the 7,936-byte stack; a host test fails if the chain grows past a pinned depth, and the bench reads the real peak.
refs: LEAD/R06; A.U30.18; A.U30.19; M.SRC_CORE.005; M.SRC_CORE.006; M.SRC_CORE.016; M.SRC_CORE.034; M.SRC_NET.125

## unreadable-config-file [significant] status=ask
decision: If a config file exists but cannot be read (I/O error, out of memory), the module runs on its defaults, every PUT to it answers Failed until the next boot, and the file is never rewritten. A readable file with a bad key keeps the one repair per boot.
NOTE: As discussed and stored here: "Damaged config files (OR138)"
refs: A.U11.20; M.SRC_CORE.043; LEAD.md resolution 9; G5/R34; OR70.a (3); OR71.a (2)

## timestamps-before-ntp [significant] status=ok
decision: Until NTP first sets the clock after a boot, readings are published with TS null, and UTCTime/LocalTime read null. Such a reading is a valid measurement, not a failed read. Once set, the clock counts as valid for the rest of the boot, even if a later sync fails.
refs: A.U10.06; REF/R04; M.SRC_SENS.089; M.SRC_SENS.090; M.SRC_SENS.091; M.SCR.049

## reflash-runbook-erase [significant] status=ok
decision: The reflash runbook erases the filesystem when a unit moves between the legacy firmware and this one, in either direction. A later update of a unit already on this firmware keeps its stored settings.
refs: A.U32 open point 1; OR59.a (1); OR52.a (2); M.DOCS.048

## wifi-off-led-pattern [significant] status=ask
decision: When the unit has permanently deactivated its Wi-Fi after a failed hotspot stage, the Wi-Fi LED blinks 0.1 s on, 2.9 s off: the hotspot pattern inverted, mostly dark, unlike every other state.
NOTE: Generally fine, and as discussed already, this shall respect the general WiFi LED setting (stay silent if turned off, apply whatever current pattern when turned on)
refs: A.U18.30; M.SRC_NET.077; M.SRC_NET.100

## scd30-calibration-readiness [significant] status=ok
decision: Following your four readiness criteria, the SCD30 publishes a readiness code and gains three user settings stored in its config file: noise floor 20 ppm (twice the datasheet repeatability), change-rate limit 10 ppm/min and window 60 s (both provisional until measured on the bench). The SCD30 reader becomes a config-file-backed reader for them; their error log stays RAM-only, as you said 'no extra FRAM chunk'.
refs: A.U15.12; REF/R06; M.SRC_SENS.051; M.SRC_SENS.052; OR98.a; OR99; OR99.a; AC_NOTES 13

## api-unknown-key-invalid [significant] status=ok
decision: A PUT that names an unknown key, an unknown sensor or a malformed sensor entry gets 'Invalid' for it in the per-field result, instead of being silently ignored.
refs: A.U19.01; M.SRC_NET.120; M.SRC_NET.123

## release-defined-point [moderate] status=ok
decision: The one merge into main is the release: it carries the version as a git tag and a short release note of user-visible changes against legacy (renamed keys, reset reason, the overnight window, compare-before-write, the new API). The stored-config and REST reference copies are taken from it. The tag is pushed only at the close, with your agreement.
refs: LEAD/R15; A.U37.10; A.U37.12; M.PROC.044; OR5; OR11.a

## lwip-retry-on-full-queue [moderate] status=ok
decision: With your send-stall fix (the send returns 'try again' instead of blocking), a connection whose send queue is full retries cooperatively until the peer acknowledges or the 5-second per-call timeout ends it. Load tests bound how much other tasks' latency and CPU share may suffer. If they fail that bound, the fix adds a short wait for 'writable' after each 'try again', and that change is put to you.
refs: AC_NOTES 21; AC_NOTES 24; A.U21.14; OR114; OR115

## humidity-helpers-removed [moderate] status=change
decision: abs_humidity() and rel_humidity() are removed from the maths helpers, with their tests. If an SHTC3 sensor is ever promoted, it re-adds the legacy formula with its own input checks.
NOTE: Keep them, they are also one of the kind "useful, complete the functional suite, small, lightweight.
Adapt the tests to be in line with the others.
refs: AC_NOTES 8; A.U12.09; A.U12.10; U12 Q1; G3/R06; OR46

## http-head-limits [moderate] status=ok
decision: The web server refuses, quietly, a request with more than 32 header lines or a request line and headers over 2,048 bytes in total, before the memory is allocated.
refs: A.U19.07; M.SRC_NET.112; M.SRC_NET.118; A.C.04 (6)

## static-no-cache [moderate] status=ok
decision: Static files are served with Cache-Control: no-cache and no ETag, so a browser asks again on every visit.
refs: A.U19.06; M.SRC_NET.124

## status-fields-added-and-left-out [moderate] status=ask
decision: /status gains HTTPDropped (requests refused at the connection ceiling, refused for a bad head, or reset early) and WifiTS (when the Wi-Fi snapshot was taken, so a stalled Wi-Fi task shows). Left out, with reasons recorded in the specification: the live open-connection count, the supervisor's task-error budget, and each notification signal's last value and triggered flag.
NOTE: Sounds good, and handle the dropped Http connections the same way as the dropped (general) connections, as we already discussed - last 24h with 24 counter buckets, no dynamic allocation and capped counters.
refs: A.U19.10; M.GEN.008; OR94.a (15)

## deactivated-snapshot [moderate] status=ok
decision: When Wi-Fi is permanently deactivated, the networking snapshot reports Mode STA, Connected false, and null for addresses and signal strength, without asking the radio.
refs: M.SRC_NET.091; A.U18.33

## ntp-synced-goes-stale [moderate] status=ok
decision: NTPSynced is true only while the last successful sync is recent: a failed resync no longer resets the staleness count, so a clock that has not synced for several intervals reads as unsynced.
refs: G6/R30; OR57.a

## ntp-no-origin-check [moderate] status=ok
decision: NTP replies get no originate-timestamp check. Only the configured server's address and port can reach the socket, and each attempt uses a fresh socket, so a late reply to an earlier attempt reaches nothing.
refs: A.U18.19; M.SRC_NET.048; OR52.a (3)

## dns-fallback-setting [moderate] status=ok
decision: The two built-in fallback DNS servers become the NTP setting DNSFallback, default '8.8.8.8,1.1.1.1', up to three IPv4 addresses, empty for none.
refs: A.U18.10; M.SRC_NET.020; M.SRC_NET.023; M.SRC_NET.043; OR56.a (2)

## hotspot-redirect [moderate] status=ok
decision: In hotspot mode, a GET for a page that does not exist is answered with a redirect to the device's page, so a phone's captive-portal check opens it.
refs: G6/R35; HARVEST_REQUIREMENTS 3.3

## envelope-codes-equal-http [moderate] status=ok
decision: The response envelope has one code catalog. A shaped HTTP error (400, 404, 405, 413, 500) carries its HTTP status as its envelope code; codes no code path produces are removed.
refs: A.U19.15; M.SRC_CORE.070

## system-command-words [moderate] status=ok
decision: Reset to defaults is sent as SystemCmd 'resetconfig', Erase FRAM as 'erasefram': lowercase, no separator, like 'mempause' and 'bootloader'. Only the exact word works.
refs: SUPP_owner_0930 design block; M.SRC_NET.121; OR121.a; OR122.a (2)

## system-command-sequence-details [moderate] status=ask
decision: Any command arriving while a reset is armed is refused; the watchdog latch is set when the command is accepted; reboot and bootloader record reset reasons 3 and 4; an early refusal changes nothing for all four commands; the SCD30's own memory is not among the stores closed during the sequence; the supervisor's own escalation stays direct and re-checks watchdog ownership after its log write.
NOTE: Sounds fine, only it should also be ensured that no more writing commands are being sent to the SCD30 during reset. Actually, this should already be the case due to the rules "only write to SCD30 triggered by API commands" and "reject any API command while waiting for the reset". This mechanism is good enough, only make sure it's working watertight.
refs: SUPP_owner_0930 open points; A.S0930.12; A.S0930.13; A.S0930.31; OR119.a; OR120.a; OR126.a (3)

## reset-reason-codes [moderate] status=ask
decision: ResetReason numbers: 0 unknown, 1 power-on, 2 watchdog (no record left), 3 reboot, 4 bootloader, 5 task-error budget, 6 supervisor starve-arm failed, 7 config reset, 8 FRAM erased, 9 command incomplete, 11-15 a boot that failed in phase 1-5, 20 C-stack exhaustion. Six boot phases are marked in RAM that survives a reset, once per transition, never in flash or FRAM.
NOTE: Good, and make the numbers clickable in the website like the errno and wrnno numbers.
refs: A.U11.05; A.U11.06; A.S0930.15; A.U30.19; M.SRC_CORE.006; OR60; OR102.a (6)

## failed-push-no-flash-write [moderate] status=ok
decision: A setting is staged first and written to flash once after it was pushed to the chip. A push that fails and restores the old value writes nothing; a successful one writes once. The window in which a power loss loses the change grows by the push time.
refs: A.U11.28; G5/R40; M.SRC_CORE.044

## one-entry-per-fault [moderate] status=change
decision: One fault leaves one entry in the persisted history: the layer that detects it persists the entry, the layers above only print to the console.
NOTE: It should rather stay as is, upstream layers reacting to a downstream fault may encounter following errors going above the original fault, so getting a notion of a traceback and blast radius of an error is actually desirable.
refs: A.U3 open points; A.U3.04; G3/R02; OR56.a (1)

## led-request-internal-queue [moderate] status=ask
decision: Your rule refuses a REST LED command at once while a signal runs. An internal notification request instead waits for the running signal up to a deadline and then queues, as legacy queued it, but bounded.
NOTE: Fine, and this for a reason: internal LED commands are guaranteed to be bounded by number and frequency, they won't flood the device. External commands might quickly flood it into exhaustion. The refusal and error message lets the external caller knows to try again later.
refs: A.U9 design note; G3/R64; OR102.a (5)

## threshold-rewrite-failure [moderate] status=ok
decision: When a resolution change lands but the follow-up rewrite of the auto-range thresholds fails, the failure is logged and the setter still answers success.
refs: M.SRC_SENS.080; A.U15.33

## pres-offset-warning [moderate] status=ok
decision: If PressOffset moves pressure outside 300-1250 hPa, the reading is still published, sea-level pressure is left empty, and a warning is logged once.
refs: A.U15.24; OR101.a; M.SRC_SENS.043

## state-code-values [moderate] status=ok
decision: VOCState: 0 blackout (first 46 samples), 1 learning (first 24 h after a fresh start), 2 settled, 3 restored from backup (first 24 h). CalLight: 0 not applicable now (fixed range or range changing), 1 suitable for calibration, 2 too dark, 3 too bright. The fourth CalLight code is the planning's addition.
refs: A.U15.19; A.U15.36; LEAD/R19; LEAD/R23; OR76; OR97.a (17)

## scd30-write-path [moderate] status=ok
decision: The settings write path moves from the config-file reader class into the base reader class, so the SCD30 can use it with its chip-stored settings.
refs: A.U4.03; A.U4 open points; OR42.c (1)

## idle-poll-rate [moderate] status=ask
decision: Every poller waiting with no deadline uses a slower idle rate; for UDP that is 100 ms (the captive DNS listener), while waits inside a DNS or NTP exchange keep the 20 ms you confirmed.
NOTE: What is the general background of this, and how and where is the rate specified and validated?
refs: A.U18.05; G4/R56; OR24

## ntp-sync-last [moderate] status=ok
decision: In the fixed boot order (construction, setup, tasks, timers), the first NTP force sync comes last, so the web server already answers while the sync runs.
refs: OR75.a; G5/R05; A.U20.06

## uart-flash-erase-overrun [moderate] status=change
decision: On dev, a flash erase during a config flush runs with interrupts off and can overrun the UART's 32-byte receive FIFO: the link loses one frame and resyncs. This is accepted as degradation, not designed away.
NOTE: On which kind of flash erase could that happen? Just normal config writing or only during the full reset to defaults? In either case, this should not happen as a random side effect. Either don't lose a frame in general (preferred, if achievable with adequate effort), or halt the UART in some way for the time it takes (feels like a workaround only, though). Come back at me for this.
refs: A.U31.01; A.U31 open point 2; SPEC J.7

## heap-floors-kept [moderate] status=ok
decision: The heap bounds checked after a full system build on the board (largest free block at least 32,768 B, survivors at most 100,000 B, nothing placed in the top 16,384 B) stay as they are; each states its basis and changes only through a new derivation of the need, never to fit a reading.
refs: G4 section 4 (heap floors); HR148; OR30.a (3)

## legacy-wip-as-intent [moderate] status=ask
decision: Code you committed in the old work-in-progress folder is read as your later intent when judging legacy parity, unless it defeats its own purpose.
NOTE: If you mean the "improved_quality" folder which we moved to the promoted files, and just using what it once contained as a reference unless stated differently, yes.
refs: G9/R02; G9/R04; OR57.a

## stale-as-fresh-every-driver [moderate] status=ok
decision: Your rule that a reading never claims a freshness it lacks binds every driver; the SCD30's 'no new data' reuse stays the one named exception with your reason.
refs: G3/R22; HARVEST_REQUIREMENTS 3.3

## sgp40-chip-identity [moderate] status=ok
decision: The SGP40 chip-identity check stays (it was observed on silicon), and the serial number read is completed to all three words; it is verified on the dev board.
refs: G3/R30; HARVEST_REQUIREMENTS 3.3

## standard-state-repair-optin [moderate] status=ask
decision: A bench session that finds the board outside its standard state (image, debug level, SCD30 values, FRAM write-protect, scratch files) fails at the start; repairing it is an opt-in flag.
NOTE: Fine, and if that happens, output a console message telling what happened and what options to repair exist.
refs: A.U26.79; LEAD/R02; A.U26 open points

## standard-board-state [moderate] status=ok
decision: Every round ends on the release dev image with the error counts saved, debug level 5, the SCD30 at its configured values, FRAM write-protect clear and no scratch files, checked by fixtures at its end and the next round's start. This replaces the hand-kept board-state line.
refs: LEAD/R02

## console-starvation-bench-test [moderate] status=ask
decision: The check that a host holding the USB port open without reading does not starve the device becomes a gated bench test; it spends 2 flash writes (debug level set to 0 and back to 5).
NOTE: Fine if "a gated bench test" means "only if additional write wear is allowed by the flag".
refs: M.HW_BENCH.082; A.U19.23; OR126.a (2)

## hand-run-hardware-rows [moderate] status=ask
decision: Five hardware rows with no test get concrete hand steps: blocking NTP on the bench network to watch the SGP40 log, timing 100 reads per driver, timing LED ramps from the console, reading recovery-rung counts from the default run, and, only if planned, a temporary image without the 100 ms hotspot settle (2 flash cycles, reverted at once).
NOTE: What are these tests good for? Are they conducted only once or shall they become part of the general testing? Which added value do we get from them (if any)? This sounds a bit like leftovers from a hardware debugging round, if these actions do not deliver any added value, we can completely drop them.
refs: M.PROC.038

## twin-tolerates-ntp-offline [moderate] status=change
decision: The twin's normal-boot log check tolerates exactly NTP's 'cannot resolve' and 'no reply' codes, and only while that boot's NTP is not synced, instead of running a local NTP server.
NOTE: A local NTP responder is built for the twin, and we can even use it for building more unit tests checking the NTP client (the usual functional, error handling, biting coverage, regression tests)
refs: A.U35.38; A.U35.39

## typecheck-stripper-text-edit [moderate] status=ok
decision: The build removes type-checking-only blocks from the frozen image with a text edit that keeps every line in place, instead of rewriting the file through Python's ast module.
refs: A.U27.04; LEAD/R13; G4/R36

## stub-versions-pinned [moderate] status=ask
decision: The stub package's exact post-release is pinned in versions.toml and checked against the MicroPython version, replacing CLAUDE.md's 'auto-derived, not a separate hand-kept pin'.
NOTE: Fine, and we need to ensure that this will be updated along with Micropython when switching to a newer release.
refs: A.U27.02; G4/R35

## comment-cap-long-lines [moderate] status=ok
decision: The 3-line comment cap counts a long comment line as several lines at a 110-character wrap; 84 existing blocks go over and are rewrapped in the same change.
refs: A.U27.28

## ci-web-filter-base [moderate] status=ok
decision: The website CI jobs decide whether to run by comparing against the last commit whose CI run succeeded, not just the previous push.
refs: A.U28.07; M.TOOL.005

## bench-sudo-checked [moderate] status=ok
decision: The bench-tier installer checks and lists the passwordless sudo rules it needs (nmcli, iw, iptables, tc, tee, picotool, timeout, systemd-run, systemctl) but never writes a sudoers file.
refs: A.U21.26

## bench-psk-fallback [moderate] status=change
decision: The bench access-point password comes from an environment variable and is set through nmcli's interactive edit mode, never on the command line or in a log. If that mode does not read piped commands on the bench Pi, the fallback is recorded as a known limitation.
NOTE: the password is a throwaway password used only once, no need for such complexity here.
refs: A.U21.19

## threat-model-table [moderate] status=ok
decision: The specification gains a table of every exposure (HTTP server, hotspot, captive DNS, NTP, UDP, USB, ...), the modes in which it exists and its disposition, under the trusted-home-LAN model you chose.
refs: A.U29.01; A.U29 open points; OR52.a (3)

## licence-notices [moderate] status=ok
decision: The captive DNS file carries 'Apache-2.0 AND MIT', scoping Apache-2.0 to the derived DNS-query class. A published image's notices include Sensirion's BSD-3-Clause text for the VOC algorithm as well as DFRobot's MIT terms. If the original captive-DNS repository is unreachable, its unsourced year is dropped rather than kept.
refs: A.U34.04; A.U34.05; A.U34.09

## wozi-move-owner-operation [moderate] status=ask
decision: The rule 'WoZi is never flashed' binds sessions and the test tiers; moving your in-service WoZi unit to the new firmware is your operation, and the runbook says so.
NOTE: This is a remainder of the promotion process. There is nothing special for any of the builds (apart from some well contained exceptions for dev, which is somewhat special). For all normal builds, especially WoZi, there are no such specialties and they shall be removed from the docs.
refs: A.U32 open point 3; OR61.a (2)

## operator-actions-one-place [moderate] status=ok
decision: DEVICE_REFERENCE.md gets one commissioning and operating section listing every action that needs a person, with its trigger: Wi-Fi setup through the hotspot, the first AmbPres PUT that starts the SCD30, forced recalibration, ISL29125 calibration, reading the reset reason, and the reflash runbook.
refs: LEAD/R14

## favicon-inline [moderate] status=ok
decision: The legacy icon returns as a 16x16 image embedded in the page, so loading the page still opens only two connections.
refs: A.U23.39; M.GEN.060

## website-display-details [moderate] status=ask
decision: Timestamps show as ages (seconds below 120 s, minutes below 120 min, hours below 48 h, then days; 'clock mismatch' below -5 s). LastTaskEnd shows '<Task> at uptime <n> s', 'invalid value' or '-'. Status codes appear as clickable numbers that show their description. A number is accepted only in plain decimal form; anything else is sent as typed and the device answers Invalid. ContMeas shows no state until you set it (its default-value mechanism goes). CalLight colours follow a fixed tone table. The SCD30 temperature offset's hint names its 0.01 °C resolution. Special-value meanings show in the hint of number fields only; a 'modules without data' line appears only when there are some.
NOTE: Fine, and maintain a reasonable number of digits per value (e.g. limit to 2 or 3 digits behind the decimal point, don't print full floats). But only for the website, the API delivers full resolution. Configured in the website config file, derived or defined from the value sourcing modules (e.g. Schema or inside the commented configs).
refs: A.U23.14; A.U23.16; A.U23.20; A.U23.21; A.U23.49; M_WEB D2-D5; M.WEB.012; M.WEB.014; M.WEB.015; M.WEB.016

## negative-backup-age [moderate] status=ok
decision: An SGP40 backup whose timestamp lies in the future (negative age) is treated as expired, not accepted.
refs: G5/R31; M_TEST_UNIT D-T13; M.TEST_UNIT.138

## no-gcc14-ci-leg [moderate] status=ok
decision: CI gets no GCC 14 build leg and the distribution compiler stays unpinned; your manual two-chroot check covers it.
refs: G8/R30; HARVEST_REQUIREMENTS 3.3; A45

## reproducible-image [moderate] status=ask
decision: The same commit, pinned toolchain and pinned host Python give byte-identical frozen inputs and the same module order in the image; the frozen website is compressed without a name or time stamp.
NOTE: Fine, but how to handle the difference between the actual build date and timestamp? They must differ for being genuine. Apart from that, everything shall be byte-identical.
refs: LEAD/R13; G6/R42; HARVEST_REQUIREMENTS 3.3; M.SCR.066

## driven-time-and-rtc-steps [moderate] status=ok
decision: Months of uptime (tick wraps, NTP cadence, counter decay, log-ring saturation) and forward/backward clock steps (first sync, offset change, DST) are proven under a driven clock in the unit and twin tiers for every device, not only by real-time soaks.
refs: LEAD/R04; LEAD/R05

## retry-pass-flagged [moderate] status=ok
decision: A test file that passed only on its retry is named and counted in the summary and logged as an item to root-cause; the retry itself stays.
refs: LEAD/R03

## twin-first-for-instruments [moderate] status=ok
decision: A committed runner runs every device script and hardware test once against the twin before it enters the hardware queue, and again after a change to it or the API it calls; exceptions are listed.
refs: LEAD/R01; OR29.a (4)

## toml-build-metadata [moderate] status=ask
decision: Device-file keys read only by tests and the bench harness (bench, hardware_family) count as build metadata, outside your 'no test-only artefacts' rule, because they never reach the image.
NOTE: Where are these keys actually stored? Come back at me concerning this.
refs: M.GEN.025; M.GEN.052; M.GEN.057; OR36

