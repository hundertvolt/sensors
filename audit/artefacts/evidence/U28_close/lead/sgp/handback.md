# Hand-back: the SGP40-in-the-idle-check root-cause and fix agent (as received, condensed)

Root cause (verified unless marked): the shared boot is a fresh `ctx.boot(*_CONN)` with SSID at its default "", so the wifi
service goes to its hotspot (`src/asy_wifi_service.py:346-349`), `network_available_locked()` is False (`:969`) and every NTP
attempt is skipped (`src/asy_ntp_client.py:406-408`). SGP40's defaults, BackupPeriod 1 and WaitTimeNTP 30
(`src/asy_sgp40_driver.py:98`, `:100`), no device overriding them: the first backup falls due at cycle 60, waits for NTP
while `voc_write` counts down, and at cycle 89 writes untimestamped with warning 35 (`:526`), then every 60 cycles. The twin's
Timer sleeps a whole period before firing (`digital_twin/machine.py:1400-1418`), so cycles only run late. One idle dev twin
(shared-boot args, GC 32768): serving at +4.0 s, W35 at +94.0 s and +155.1 s (`run1.out`). The idle check
(`scripts/_digital_twin_scenarios.py:313-336`) fails any unstated move; no scenario states SGP40.

Why it passed before: gate1b's dev shared group (30 scenarios) ended at 83.9 s at 32768 and 73.4 s at -1; the other devices
at 61-69 s. CI's shared phase ran at least 1.14 x slower in run 39335426899 (inferred: the early log lines were beyond the
job-log tail the tool returns); the step start to the end of `a_command_right_after_the_first_answer_resets_cleanly` took
404.7 s at 32768 and 291.6 s at -1, against 156.9 s and 138.9 s in U27's green run. Every device and both stages were exposed.

Options weighed: NTP synced for the shared boot (plants a station config, breaks the three shared hotspot scenarios);
the backup period past the suite (plants SGP40 config, hides the product default); excusing W35 when witnessed (exact, needs
new twin instrumentation). Chosen: retire each shared twin before the deadline, 60 x BackupPeriod + WaitTimeNTP - 1 read
cycles of 1 s after the spawn (a lower bound), with a 30 s per-scenario budget (about 3 x the longest sharing scenario,
9.8 s), and a named overrun in the idle check; the lead changed the overrun to fail only when a count moved.

Proof: the new tests failed on `836689a` (`fix/red.txt`: the third of three 40 s scenarios with CI's exact message; a 100 s
scenario blamed for the move; the derivation's constant missing) and pass on the fix (`fix/green.txt`, the lead's
`green_lead.txt`, 41/41); the dev harness alone 49/49 at 32768 (retired after #22 at 62.9 s, 462 s) and at -1 (after #27 at
59.5 s, 431 s) (`fix/h32768`, `fix/hneg1`).
