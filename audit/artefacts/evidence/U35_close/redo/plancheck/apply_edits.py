"""Apply the plan check's corrections to PLAN.md; every old text must occur exactly once."""
import re, sys
path = sys.argv[1]
text = open(path).read()
lines = text.split("\n")

def row(prefix):
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]

NEW_ROWS = {
"| B1 logging and catalog |": "| B1 logging and catalog | `asy_print_log.py`, `buildgen/error_catalog.json`; the `report_if_fatal()` sites in every module | The C-stack reboot (the owner's \"ok\") in smallest form: the 123 calls become one check in the logger, placed before its FRAM write, plus explicit calls at the 5 handlers that log nothing (`asy_base_classes.py:132`, `asy_captive_dns.py:190`, `asy_fram_driver.py:174`, `asy_system_service.py:474`, `asy_webserver_service.py:203`) and the Microdot hook. The console lines that print a caught `MemoryError` in classes with no logger (UART driver 11, UDP socket 7, RegionBuffer, the COBS codec) and the logger's own below-level arm: their fate is clarification (d), widened to them, since the owner's \"Option 1\" (2026-10-20) set the unit tests' log level and no owner word covers these lines. Catalog rows of removed codes go, with no placeholder, and the 6 existing placeholders go (decision 6); the no-reuse rule's text says it applies from the release on. Runs alone, because it touches every module. Clarification (d) first. |",
"| B2 core |": "| B2 core | `asy_base_classes.py`, `asy_system_service.py`, `asy_config_manager.py`, `math_helpers.py`, `asy_api_response.py` | Go: `ResetBits` in `/status` with its website row (the decoded `ResetReason`, OR60, stays); `ConfigUnpersisted` in `/status` with its website row (the flag stays for the shutdown flush); W69 with `absent_at_boot`, a missing config file returning to the pre-audit persisted warning (one per boot), with OR136.a's write-once kept; E115; the uptime re-arm; the 1,200 ms escalation bound (the reset record is written before it). Changed back: a chip-setup failure on the normal ladder, mild rung first (OR113); `rel_humidity()` clamps again, as legacy and the pre-audit code did (the owner's note kept the helpers and asked for the tests to be aligned; the no-clamp rule is agent text). Kept: the mempause deadline (decision 3, item 2), its two cascade parts judged in the ledger; the recovery ladder (smaller form); the reset path; the system commands; the staged write; the newest-entry rule; the counter caps (OR103); the measured uptime (OR101). The wet bulb's cold-dry corner: clarification (h) first. |",
"| B3 storage |": "| B3 storage | `asy_fram_driver.py`, `asy_fram_manager.py`, `asy_crc_checks.py` | Go: the lost-FRAM chain, whole (decision 3, item 1); the chunk read's `MemoryError` catch and the two rows of the same kind beside it (A-M9, A-M10, A-M11, judged in the ledger). E28 shrinks to one entry at setup for an unreadable store; its run flag and its heap-failure arm go, and a full FRAM stays silent (owner, 2026-09-16: \"we do not even add errno/wrnno for the out of FRAM memory\"). Kept: the per-owner CRC seed, which is the layout-shift fix (owner, 2026-10-28); the blank chunk; the unreadable store; a declared FRAM that never sets up; the CRC32 in two 16-bit words (a confirmed gap, as landed). Clarification (e) first. |",
"| B4 buses and sensors |": "| B4 buses and sensors | `asy_i2c_driver.py`, `asy_spi_driver.py`, the SCD30, SGP40 (with `voc_algorithm.py`), BMP3XX and ISL29125 drivers | Go: the I2C and SPI \"no bus\" contract at every consumer (rp2's constructor cannot fail with its stored arguments, `machine_i2c.c:61-118` at v1.29.0); the BMP3XX power-on detector with W71, its conversion wait and scratch view back to the STATUS poll; E27 at both its sites, BMP3XX and SCD30 (the range gates stay; a rejected reading logs as the module's read failure); W73; the ISL shadow compare back to after a failed write, W75 back to the pre-audit console line; the SGP40's sample-age check and `None` branch, its restart back to the restore, its own \"no backup\" warning back; the VOC constants back to the per-sample port. Shrunk: the I2C clear as one clock-out routine, the short-ACK path in about 4 lines. Kept: I2C-6/7, the ISL settle horizon, the SGP40 restore cycle, a wedged bus at boot, a chip failing in operation. VOC-3's restore validation is judged in the ledger. |",
"| B5 network |": "| B5 network | `asy_wifi_service.py` (form only), `asy_ntp_client.py`, `asy_dns_client.py`, `asy_captive_dns.py`, `asy_udp_socket.py`, `asy_webserver_service.py` | Go: the web server's start retries and W62 (one start; asyncio sets `SO_REUSEADDR` and rp2's lwIP builds with `SO_REUSE 1`, so a restart rebinds at once); WS-2's head refusals, the HTTP version refusal among them, except the `Content-Length` check, and WS-9's quiet print with its merge list (decision 3, item 3); W16; the captive DNS re-raise; the NTP 44-47-byte refusal; the NTP cadence chain (NTP-12, NTP-13, NTP-15); the resolver's passed-in logger and `(address, cause)` widening (a diagnostic beyond need; one E67 as before); the stored NTPHost/DNSFallback re-check. Kept: `TickSeconds` with its owner-decided users (SysUptime, LastSyncAge, WifiUptime, the LED pause); the Wi-Fi behaviour as decided (form only); the zero NTP timestamp; the 512 B receive with one yield per datagram; the listener close; the head bounds; a trace per dropped connection; W12. |",
"| B6 UART |": "| B6 UART | `asy_uart_driver.py`, `asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py` | Go: the zero-length guard; `PieceBuffer.read_at()`, whose one user is the responder's piece reply. Kept: `PieceBuffer.trim()`, which `uart_get()`, the SET receive and `readline()` call; the construction refusals E91/E92 and their build mirrors, the pre-audit pattern of a standalone module that refuses its own bad parameters (the ledger may shrink their form); the DMA ring; the hazard mode; the link's `initialized`. The codec's decode-size change and its removed counter are judged in the ledger, the codec being a real feature of the module. The wire format stays untouched, and every change gets its changelog entry. Clarification (c) first. |",
"| B7 LED |": "| B7 LED | `asy_neopixel_driver.py`, `asy_notification_service.py` | Not a rewrite: the module's audit diff is mostly names, typing and comments, with five behavioural rows. The overlay rewritten every 300 s (NP-5, 5 lines) goes back to the pre-audit wait, which also removes the lost shutdown cancel. The entry sanitiser (NP-3, 11 lines) goes back to the pre-audit clamp, per channel with the 0.1 s floor; its 60 s cap and its move to the entry go. NP-4's defined end state is settled in the ledger, since the two scans differ on it. The internal request queues at its deadline, as the approved text says, and W67 goes (DECREV 4.4). The notification's sample-age check and its `State` field go. Kept: the refusal of an external command while a signal runs (NP-1), the bounded internal wait (NP-2), the REST refusal, the overnight window (OR69), the measured LED pause (OR104). |",
"| B8 build chain and generated code |": "| B8 build chain and generated code | `buildgen/`, the generated modules, `devices/*.toml`, `js/` and `html/` frozen into the image | Go: the build checks that no device TOML can trip (about 314 lines), except a rule whose violation would make a boot refuse or boot-loop: of the three I2C timeout checks, `bus.i2c-timeout-max` stays while the dominated boot-clear budget and loop-hold bound go, and the UART ranges stay as the build mirror of B6's kept refusals. The read triggers' bus-spread order (refuted: on all six devices it equals the construction order). The website lines with no recorded agreement (the items the owner approved stay; `PICTURE.md` 5), among them the page build-date stamp and the website rows of the status keys B2 and B7 remove. The device TOMLs follow their drivers (the UART keys follow B6, the `@tunable` tags R2's Part N scope). Kept: the generated boot entry's confirmed gaps (the emergency exception buffer, the loop-end labels). |",
}
for prefix, new in NEW_ROWS.items():
    lines[row(prefix)] = new
text = "\n".join(lines)

def rep(old, new):
    global text
    n = text.count(old)
    assert n == 1, (n, old[:80])
    text = text.replace(old, new)

rep("Written by the lead, 2026-10-28 13:20 UTC. A plan only: nothing in it starts without the owner's go-ahead.",
    "Written by the lead, 2026-10-28 13:20 UTC; checked row by row against the sources the same day (`plancheck/`). A\nplan only: nothing in it starts without the owner's go-ahead.")

rep("- **All seven decisions were taken by the owner on 2026-10-28** (section 6). R0 starts only with its own go-ahead.",
    "- **Checked row by row (2026-10-28, on the owner's request).** Every row was checked against the code, the pre-audit\n  tree, the owner's rows and the pinned sources, and corrected where the evidence did not hold\n  (`plancheck/CHANGES.md`); independent agents then tried to falsify the claims (4.4, rule 11).\n- **All seven decisions were taken by the owner on 2026-10-28** (section 6). R0 starts only with its own go-ahead.")

rep("""- The pushed audit head is `fc509999`. Its product tree equals the integration head `497b3eda`.
- The 97 integration commits since the redo's base are only in this container (`audit/u35-int`); the pushed snapshots
  carry their trees, not their history. The plan does not need that history. If the owner wants it kept, it can be
  pushed as its own branch, with the owner's permission.
- CI on snapshot 17 runs; on snapshot 16 it was red only on `test_twin_record`'s two checks. All MicroPython tests pass
  at both GC stages.""",
"""- The pushed audit head is `0603e74d` (snapshot 18). Its product tree equals the integration head `497b3eda`.
- The integration history (300 commits since the redo's base, 97 on the first-parent line) stays in this container:
  its messages carry lane names, which no pushed text outside the evidence folder may. Its messages and changed files
  are kept in the evidence folder (`redo/int_history.txt.gz`). The plan does not need the history itself.
- CI on snapshots 16 and 17 was red only on `test_twin_record`'s two checks. All MicroPython tests pass at both GC
  stages.""")

rep("""- **The paused lanes close.** Their patches are already in the evidence folder; their worktrees go once the patches
  are checked complete. The register's U35-U37 rows point to this plan.
- **The twin record goes** (2.4), so that CI is green from the start.
- **DECREV 9's three static checks** run before B1: the logger-side C-stack check at a near-exhausted C stack, on the
  Unix port (item 3); the three BR2 fixes, read at the parent of `7008730e` against v1.29.0 (item 5); and the
  2026-10-07 proposal behind the exception-handler guard (item 6). Each decides its batch item before the batch
  starts.""",
"""- **The lanes close.** The paused lanes' patches are complete in the evidence folder (checked 2026-10-28: no file in
  their worktrees is newer than its patch; CRr2d's holds no work; CMr1n, RF1 and CM4 never started). Their worktrees go,
  and so do those of every merged lane. The register's U35-U37 rows point to this plan.
- **The twin record goes** (2.4), so that CI is green from the start: `tests_hardware/twin_record.json`,
  `tests_scripts/test_twin_record.py` and `scripts/record_twin_instrument_runs.py` (about 1,835 lines), with their
  references in BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md, `digital_twin/README.md`,
  `digital_twin/run_device_script.py`, `pyproject.toml`, `tests_hardware/README.md` and Part N. `tests_hardware/
  twin_board.py`, which runs the hardware tests on the twin (`--twin`), stays with its test.
- **DECREV 9's three checks** run before B1: the logger-side C-stack check at a near-exhausted C stack, a Unix-port run
  (item 3; its board half is REPORT 7's item 1, not run, 3.2); the three BR2 fixes, read at the parent of `7008730e`
  against v1.29.0 (item 5); and the 2026-10-07 proposal behind the exception-handler guard (item 6). Each decides its
  batch item before the batch starts.""")

rep("""**Order.** B1 runs alone, then B2.""",
"""The table names each batch's main items; the ledger judges every hunk, unnamed ones included. Outside R1: `ext/` stays
as re-vendored (Microdot v2.7.0, byte-identical upstream; OR129.a, OR131.a); `src/LICENSE-captive_dns` (path names
only) is R4's.

**Order.** B1 runs alone, then B2.""")

rep("""- **Retired first, in R0:** the twin record (`tests_hardware/twin_record.json`, about 2,260 lines with its tests). It is
  audit machinery and the only red in CI. With it gone, every later push is judged on green CI.
- **Each test and tool file is classified once.** The classes:""",
"""- **Retired first, in R0:** the twin record (2.2, about 1,835 lines; `twin_board.py` and `--twin` stay). It is audit
  machinery and the only red in CI. With it gone, every later push is judged on green CI.
- **Each test and tool file is classified once** (`tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`,
  `digital_twin/`, `scripts/`, `toolchain/`, `mockdata/` and the CI files). The classes:""")

rep("""    `micropython_overrides.py` included; OR15.a's summary block): kept, slimmed where it repeats itself;
  - it is audit machinery or docs policing born in the audit (`test_citations.py`, `test_decision_vocabulary.py` with
    its 393-line allow-list, the repo-scan reader's own tests, the ~1,700 lines that pin SPECIFICATION.md tables, the
    bite self-tests of the tests): removed;""",
"""    `micropython_overrides.py` included; OR15.a's summary block; the repo scanner's own tests, which test the reader
    the owner's comment-cap gate runs on): kept, slimmed where it repeats itself;
  - it is audit machinery born in the audit (the bite self-tests of the tests, which OR21.a (2) did not adopt; the
    files that pin SPECIFICATION.md tables, about 1,700 lines, each classified with its owner basis checked, since the
    UART changelog rule and Part N's OR30.a scope are owner rows): removed;""")

rep("""  The owner rules stay in full: the comment cap gate, the gc-site checker, the memory-gate agreement, the persistence
  marker completeness and the four-tier bus hazard files.""",
"""  The owner rules stay in full: the comment cap gate, the gc-site checker, the memory-gate agreement, the persistence
  marker completeness and the four-tier bus hazard files. The two decision-records checks (`test_citations.py`,
  `test_decision_vocabulary.py`, the owner's prevention rule 5, OR68 "4. yes") stay until clarification (i), with
  their allow-lists only shrinking.""")

rep("They build B3 records and", "They build group-B3 records and")
rep("**R3 is done when:** every B3 owner row has", "**R3 is done when:** every group-B3 owner row (`PROJECT_AUDIT_PLAN.md` 3.2) has")
rep("**R4, the docs, written once from the final state** (B4's rows):", "**R4, the docs, written once from the final state** (the group-B4 owner rows):")
rep("| 53 the owner's latest test demands | partly | R3: the B3 rows are its checklist |", "| 53 the owner's latest test demands | partly | R3: the group-B3 rows are its checklist |")

rep("  - the queue in order, with expected outcomes and the wear budget;",
    "  - the queue (BACKLOG.md's \"Real-hardware work still owed\", which replaced OR8.a's queue file) in order, with\n    expected outcomes and the wear budget;")

rep("| 33-35 forty days, dropped wake-ups, counter caps | done | stay (the caps are cheap bounds the owner wants) |",
    "| 33-35 forty days, dropped wake-ups, counter caps | done | stay (the caps: OR103, \"No unbounded counters anywhere\") |")
rep("| 49 every instrument through the twin runner | partly | the twin record retires in R0; OR21.a's twin pointing goes to R3 |",
    "| 49 every instrument through the twin runner | partly | the twin record retires in R0 (`twin_board.py` and `--twin` stay); OR21.a's twin pointing goes to R3 |")

rep("These are two of the owner's statements that pull apart (DECREV 6).", "Each is a pair of the owner's statements that pull apart (DECREV 6; (i) found by the plan check).")
rep("- **(d)** the console at DebugLevel 0: OR35.a against Q6's \"Option a\" (batch B1);",
    "- **(d)** the console at DebugLevel 0: OR35.a against Q6's \"Option a\", and with it the console lines that print a\n  caught `MemoryError` in classes with no logger, which no owner word covers (batch B1);")
rep("- **(h)** the wet bulb's cold-dry corner against \"Adapt the humidity to the verified range\" (batch B2);",
    "- **(h)** the wet bulb's cold-dry corner against \"Adapt the humidity to the verified range\" (batch B2; the\n  `rel_humidity()` clamp is not part of it);")
rep("  degradation (batch B6).\n",
    "  degradation (batch B6);\n- **(i)** the two decision-records checks: the owner's prevention rule 5 (OR68 \"4. yes\", CLAUDE.md's decision records)\n  against \"The audit verification machinery is just a temporary tool\" (2026-10-28) (R2's checkpoint).\n")

open(path, "w").write(text)
print("ok")
