cr2 hand-back, written by the agent (Tue Nov 10 07:02:46 UTC 2026)

Read-only, tree `S/wt-u35int` at c4fc72ac against 25caf528 (no tree edited, no runs but git, grep, jq, pdftotext). Two scratch scripts holding the filter pattern itself were deleted. Ledger `S/u35r/r5/CREDIT2_ledger.tsv`: 117 rows, tab-separated, no header (path:line at c4fc72ac with the input line as "in :N" | credit date | rule | record citation(s) | new plain form | consequence). Input lines were mapped from 6aec784f by exact line text; :4329 was re-wrapped (now :4311), :6791 is gone (row removed by 39e18d2a today). Scratch only in `ftmp_cr2/` (filtered).

## Counts
R0 11, R1 8, R2 24, R3 8, R4 66, R5 0, LEFT 0.
- R0: BACKLOG.md:117, tests_hardware/README.md:1143, test_end_to_end_timing.py:155 (torn-write tolerance), BACKLOG.md:429, CLAUDE.md:477, :543, SPEC:3381, :4960, :6220, digital_twin/_fram_chip.py:249, _scd30_chip.py:199.
- R1: the engineering-local labels (DP L10 at CLAUDE.md:722, SPEC:12085, :5359; L56 at SPEC:3809; L49 at SPEC:729) -> agent design kept by OR71.a (0); SPEC:3666 (owner's 2026-11-06 W65 ruling); SPEC:6714 (OR68.a (2), deferred flush); UART_C_PORT_CHANGELOG.md:133 (OR28, global catalog).
- R3: THIRD_PARTY_LICENSES.md :85/:179/:230/:240/:261 and three bench-test docstrings: who asked or flagged goes, the fact stays.

## Headline results
- Owner's own commit 8c4a73d5 (2026-07-13, the improved-quality WIP code) backs by content 10 rows CREDIT had UNBACKED: the SCD30 50 ms and SGP40 3 ms waits (SPEC:11698, :11778, :12020, :12024, gone :6791), the storage pause (SPEC:328, asy_fram_manager.py:589), the VOC state fields (voc_algorithm.py:105), the never-dropped reset (asy_sgp40_driver.py:240), the boot signature (asy_system_service.py:197). Each shrinks to what the code shows; the "tested", "None" and split-retry parts become the agent's.
- DP A2-03 plus OR68.a (2) back the hand-kept status/errcount catalog (SPEC:10205, :10237, :10517, :11369); answers.json heap-floors-kept (ok, 2026-10-02) backs test_memory_stress.py:122; OWR 2026-10-28 (Wi-Fi as built) backs SPEC:503 and two test lines; OWR 2026-10-27 backs SPEC:4741; OR113 backs SPEC:3864's smallest-step rule; OR47 backs SPEC:8931; DP A48 via OR68.a (1) backs SPEC:4311's watchdog backstop.
- Merge e5d2c43 (2026-09-19) dropped origin/main's 09-13/14 text before 25caf528: two R0 items are restorations of pre-audit agent work, not new inventions: the torn-write tolerance (699836e) and the starter role definition (080cde3b).
- R4 sources found in the repo: SCD30 Interface Description 1.4.1 (AmbPres 0) and 1.4.9 (firmware version), the MB85RS64V/MB85RS2MTA CS pin tables (the five hijack lines), the three BMP3xx datasheets, a reproduced quirk (0cb214b2, size-0 chunk), the Pi 4's one radio. Numbers with no source: 20 ms UDP poll step, 200 ppm CO2 floor, port 8080, the four-minute figure (derived, unmeasured).
- Stale text: UART_C_PORT_CHANGELOG.md:133 says the link numbers codes from 10; the code uses the global catalog bands (E 75-99, W 54-59).

## Code consequences
None from R1-R5: every outcome is a credit or wording change, comments included (G: asy_fram_manager.py:509/559/589, asy_sgp40_driver.py:240/623, asy_system_service.py:197/311, voc_algorithm.py:105; C: 12 devices/*.toml comment lines; T: digital_twin, tests, tests_hardware, tests_js lines).
R0 growths, not judged, each to its unit for the two source rules: the bench test's FRAM_STATUS_BYTE/FRAM_BLOCK_INVALID tolerance (T; the test resets inside SPI writes on purpose, a demonstrated need is there to cite); tests_scripts/test_import_placement.py and the module-load rule (T; OR141.a (2), owner ok 2026-10-05, calls that rule unchanged); the twin's not-loaded notice on a bad state file (T, 311aef80); the starter role definition (P9, its naming check T); doc-only rules BACKLOG.md:429, CLAUDE.md:477, :543, SPEC:3381 (P9).

## LEFT
None. Close to one: SPEC:12009's 20 ms poll step has an open owner ask on the review page (idle-poll-rate, 2026-10-02, a question about the rate's background). That is no conflict and nothing changes, but the question is still unanswered.

## Not checked
- Record lines holding a filtered word were invisible to me; one could back or contradict a row (Wi-Fi most likely).
- Who wrote the code inside 8c4a73d5 (the same commit carries a Claude-written PROJECT_NOTES.md); I rely on the brief's author rule.
- DP E05 (SPEC:1305/:1307) is recovered plan text that was never itself put to the owner.
- Whether c4fc72ac's Wi-Fi machine is still exactly the 10-28 build; row 8's hash 1e2c001; the content of U14 Q5 option C past its answers line. arduino/ not read.
