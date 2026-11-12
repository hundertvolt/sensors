R4 falsification, written by the agent (Thu Nov  5 10:10:32 UTC 2026)

Tree: `S/wt-r4f`, detached at `837697e9`, against base `33974760`. Old texts were read with `git show 33974760:<path>`.
Runs, through `S/u35/lead/run.sh`, one at a time, seven of the eight allowed:
`r4f_help_base` (test_tool_help.py -k readme: 25 passed), `r4f_mpy` (mpy-cross on both driver versions),
`r4f_help_rowdel` and `r4f_help_optadd` (planted breaks, both restored, `git status` clean afterwards),
`r4f_citations` (15 passed), `r4f_vocab` (6 passed), `r4f_cap` (655 passed).
Every planted break was restored with `git -C S/wt-r4f checkout -- <path>`. Nothing was committed.

## 1. No rule lost: REFUTED on "meaning unchanged" (no rule is gone)
I compared 14 rules, old text against new: the hardware go-ahead, the dead-man's switch, the br0 MAC, FRAM logs
before clearing, credentials, loop blocking, the memory gates, both wear rules, `_boot.py`, both vendoring rules,
the hazard tiers, the WoZi/own-build rule, the exception precedent and UART. Every one is still there. The go-ahead,
`_boot.py` and loop-blocking rules are word for word the same, and the rest lost only story text. Two rules now
mean something different, and one pointer got thinner:
- **The exception precedent got narrower.** At `33974760`, CLAUDE.md:70-85 let the precedent extend to "a similar
  'don't touch this WIP/vendored code' rule elsewhere in this file". It named the legacy `microdot.py` rule and the
  `_boot.py` rule. Now CLAUDE.md:63-68 says the exception "never reaches the legacy tree". This matches the
  owner's legacy rule (2026-09-11) and the drift found in audit/pass3/H1.04, but it is a change of meaning, not a
  rewording. CLAUDE.md's own change-classes rule (CLAUDE.md:481-483) says drift in a recorded rule "is not reworded:
  it goes to that list" (BACKLOG.md's owner-question list).
- **Testing against the C side flipped.** At `33974760`, CLAUDE.md:155-157 said the C-side hardware "can be
  connected to the dev board, making the promoted module testable against the genuine second implementation". Now
  CLAUDE.md:137-139 (and the UART changelog) say testing against it "belongs to the post-audit reconciliation
  (owner, 2026-09-25)". OR5.a supports this ("the C port stays out of scope, anything there is post-audit only"),
  but the meaning changed.
- The claim holds only if lane B's report lists both as adopted changes. I could not find that report.
- **One pointer got thinner (hazard tiers).** At `33974760` the rule named the flash tier's real sweep,
  `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py`. CLAUDE.md:279-281 now sends the
  reader to C.8 as "the one list", but C.8 (SPECIFICATION.md:4100-4165) names only `flash/test_bus_concurrency.py`.
  The sweep script is named only in K.7 (SPECIFICATION.md:10300).
- The WoZi rule became "a device's result counts only from its own build", as OR140.a (18) asks. It dropped the
  fact "dev's own firmware covers the shared SCD30/SGP40 bus" and OR70 item 8's quote. The rule itself is intact.
- The dead-man's-switch rule is intact, but the script it relies on is now broken: see "Outside the claims" (1).

## 2. Owner words: REFUTED
I sampled 26 owner tags. 22 match their source verbatim or as a stated decision: OR10/OR10.a, OR12, OR12.a, OR27,
OR43.a, OR44/OR44.a, OR51, OR57, OR61, OR70, OR81, `b5502c8`, the 2026-10-02 answers.json note, REGISTER U33's
2026-10-21 answer, the rulings file's 2026-10-29, 11-02 and 11-03 lines, DECISION_PROVENANCE A41, and U36a.009 for
2026-09-18. Three do not:
- **tests_hardware/README.md:1355-1356.** "(the write never reaches the chip, owner, 2026-09-04)" and "(it never
  returns the real data, owner, 2026-09-04)" are bench measurements made by an agent session. The old text, from
  `31c4cc1a`, reads "Confirmed empirically (2026-09-04, this bench unit)". They are not the owner's words or
  decisions.
- **SPECIFICATION.md:11711.** "(owner, 2026-10-02: "2 settled")": the owner's recorded answer to the decision card
  `state-code-values` is `"status": "ok"`, `"note": ""` (audit/review/answers.json:242-246). "2 settled" is the
  card's own text (audit/review/decisions.json:703-707). The decision is the owner's; the quote is not.
- **CLAUDE.md:65-67 (weak).** The quoted "still requires the owner's explicit authorization each time, scoped
  narrowly to the specific fix, not a general license" is tagged (owner, 2026-07-30, `1e4cdfe`). That text is what
  the 1e4cdfe session wrote into CLAUDE.md. The commit message only says "The project owner can authorize a
  scoped, severity-justified exception". Nothing shows it is the owner's own wording.

## 3. Facts: REFUTED
I checked 31 facts. 29 match the tree or their source:
- MicroPython at /root/pico-toolchain (v1.29.0):
  - `py/mpconfig.h:2148` (backlog 2)
  - `ports/rp2/rp2_flash.c:168-174`
  - `ports/rp2/mpnetworkport.c:86-100`
  - `ports/rp2/machine_i2c.c:125`/`:147`
  - `extmod/modlwip.c:64` (10 s) and `:1008` (`STATE_ACTIVE_UDP`)
  - `lib/lwip/src/core/tcp.c:2070`
  - `icmp.c:258-283`, lwIP `77dcd25`
  - `cyw43_ll.c:1126-1128`
- Datasheets:
  - RP2040 Table 427 (rp2040-datasheet p.429-430) matches the new UARTRSR comment
  - W25Q16JV tSE 45/400 ms and tPP 0.4/3 ms (datasheet AC table); 5x400+43x3 = 2129 = `_FLASH_HOLD_MAX_MS`
- Constants and defaults in the tree:
  - `DEFAULT_LOG` holds 10 entries
  - `l1.unix_heapsize` 16M
  - `uv_sync_retried.sh`: 3 attempts, 10 s / 20 s
  - `PER_FILE_TIMEOUT_S` 240, `TESTS_SCRIPTS_TIMEOUT_S` 1200
  - the port lock's path, environment names, message and ports (53, 18080)
  - CI `needs`/`if` per job, as CLAUDE.md:764-776 lists them
  - `disallow_any_explicit` and `ignore-without-code` in all three mypy configs
  - the GMT/DST/NTP offset defaults and the EU switch rule in `cettime()`
  - the hotspot opening at once with no SSID (`asy_wifi_service.py:346`)
  - dev's `rx_ring` 8192, and 4,608 B = 11,520 B/s x 0.4 s
  - the README CLI defaults (preview port 8000, the web work dirs, `FROZEN_HTML_WORK_DIR`, `_FAULT_DEVICE_OPS`)

Two are wrong, in the `stall.flash_program` row (SPECIFICATION.md:6701), which R4 rewrote; R4 changed only its
measured-value cell:
- "the reply wait, `_read_frame()` (`asy_uart_comm.py:715-729`)": `_read_frame()` is at `src/asy_uart_comm.py:692-703`.
  Lines 715-729 are `_recv_train()`.
- "`ready()` reads the fill level ahead of the deadline (`asy_uart_driver.py:245-250`, `:715-722`)": that check is at
  `src/asy_uart_driver.py:702-710`. Lines 715-722 are the MemoryError report and the closing yield.
Both citations were already stale at `33974760`, but they now sit in a line the round added.

## 4. No history: REFUTED
The ten worst instances in changed regions:
1. SPECIFICATION.md:5622-5623: "one did: `tests/test_uart_comm_hazard.py`, 84/85, on a tree whose (e) and (f)
   stages were both 85/85, 2026-09-22". These are test counts over time.
2. SPECIFICATION.md:5626: "(run `34755468619`)", a run ID.
3. SPECIFICATION.md:8621: "128 commits of a conflicted branch once went unverified, 2026-09-18", an incident.
4. tests_hardware/README.md:1471-1473: "A run once exhausted its attempts with that in place; its cause is still
   open", an incident.
5. tests_hardware/README.md:1561-1567: "The full test-suite sweep … traced each domain's real call chains … What it
   closed is in the sections above". This tells a past activity, not a fact.
6. tests_hardware/README.md:1554-1557: "were `ruff`/`mypy`-clean but not yet run on silicon when written: a first
   cut for the next real-hardware session".
7. README.md:1097-1099: "… a `requires-python = ">=3.10"` that let `uv sync` build a venv without `tomllib` … was
   found only this way". This says who found what.
8. SPECIFICATION.md:11376: "(C.4.2's one staleness rule, owner, 2026-09-29, replacing "reported as `None`")". This
   describes what the rule replaced.
9. SPECIFICATION.md:2145-2146: "(2026-09-04); B.13 holds …", the tail of "real-hardware verification is DONE — both tiers
   run clean … (2026-09-04)".
10. SPECIFICATION.md:1769: "(HTTP 500 or 504 observed on 2026-09-13, -14 and -21)". This is the mildest of the ten:
    an outage log used as evidence.

Notes from unchanged regions:
- BACKLOG.md:31: "has now run once, beyond bus-hazard's own corner".
- tests_hardware/README.md:1585: "(broadened from SCD30-only to all persistence, 2026-09-17)".
- SPECIFICATION.md:2145: "verification is DONE".
- tests/test_asy_udp_socket.py:1521-1811: "Fifth pass"/"Sixth pass" comment headings.

## 5. README CLI reference: REFUTED (the test's sensitivity)
At head, every block matches its tool's `--help` (`r4f_help_base`, 25 passed). The test still misses two kinds of
break.
- **A removed row is caught only when its option appears nowhere else in the block.**
  - Run `r4f_help_rowdel` deleted six rows.
  - Five of them still passed, because the block's synopsis line names the same option:
    - README.md:843 `--coverage`
    - :918 `--duration NAME`
    - :995 and :1005 `--stage-only`
    - :1080 `--wiring-plan PATH`
  - Only :1057 `--skip-npm` failed.
  - Cause: tests_scripts/test_tool_help.py:147-149 compares the set of option names found anywhere in the block.
- **An added option is caught only when it reaches `--help`.**
  - Run `r4f_help_optadd` added two options.
  - An argparse option in `scripts/preview_server.py` (`--bogus-flag`) failed, as it should.
  - A `--quiet) : ;;` case branch added to `scripts/test.sh` passed. `bash scripts/test.sh --quiet --help` accepted
    it, yet neither README nor `--help` names it.
  - Cause: the shell tools' parsers are not compared with their usage text.

## 6. The one checklist: STANDS
- Part K opens with K.0 (SPECIFICATION.md:10085-10096), with its record and owner sourcing (OR10/OR10.a verbatim).
- Every step K.0-K.11 carries an *every module* / *a sensor driver* qualifier.
- `.claude/skills/integrate-module/SKILL.md` is 21 lines, names its three inputs, points into Part K and repeats
  none of its steps.
- `git grep -i checklist` outside `audit/` finds no doc calling Part D the checklist for adding a module.
  Part D is "the quality checklist" (README.md:1217) or "the quality bar" (Part K).
- Notes:
  - SPECIFICATION.md:10419 still calls Part K "the per-driver checklist". This is unchanged text, stale now that
    Part K covers every module.
  - C.8's "own promotion checklist" (:10283) and C.11 point 9's checklist (digital_twin/README.md:1180) are
    further checklists beside K.

## 7. Headings: REFUTED (one citation)
- The heading diff of SPECIFICATION.md shows only the changes claimed: Part 0 (with 0.1-0.5), K.0, I.6 moved ahead
  of Part J with the same number and title, and E.2.1-E.2.3 demoted under E.2 with the new E.2.2. A `# PROFILE:`
  line at :2189 sits inside a code fence (7 fences before it).
- Every SPEC Part/section citation outside `audit/`, `arduino/` and `legacy/` resolves. My own scanner found 0
  unresolved (it joins wrapped lines and covers `Part 0` and second items after "and"), and `r4f_citations` passed.
- One break: PROJECT_AUDIT_PLAN.md:2522, which sits outside `audit/`, still cites "`tests_hardware/README.md`
  tenth pass". That section title was renamed in `54def63f` (it is now "Tier parity beyond the bus hazards").
- No other old tests_hardware or README title is cited anywhere.

## 8. Code untouched: REFUTED (one item)
What holds:
- The only `src/` change is the comment block at `src/asy_uart_driver.py:76-78`. Its .mpy is byte-identical to
  `33974760`'s, both plain and `-march=armv6m` (`r4f_mpy`, sha256 `406709cf…`).
- `js/templates.js` and `html/style.css` changed comments only.
- The two `devices/*.toml` changes are header comments.
- `src/asy_uart_comm.py` is unchanged, so the wire format is untouched.
- No changed comment block exceeds 3 prose lines or 120 characters a line, and `r4f_cap` passed.

What is false: "every other `.py` change is a comment". tests_scripts/test_tool_help.py gains code: `_REFERENCE` and
`_OPTION` (:58-61), `_run_help()` (:71-80) and a new parametrized test (:141-149).

## 9. Allow-lists: STANDS
- The diff removes 90 lines and adds none: 66 in `_citation_allowlist.txt` and 24 in `_decision_vocab_allowlist.txt`.
- No removed decision-vocabulary prefix is still in its file.
- Of the removed citation tokens, only two README `AUDIT_PLAN.md` entries still match, and only as substrings of
  `PROJECT_AUDIT_PLAN.md`, which resolves; the bare `AUDIT_PLAN.md` citations are gone.
- `r4f_citations` and `r4f_vocab` both pass on the pruned lists.

## 10. Nothing else: STANDS
- A grep outside `audit/` and PROJECT_AUDIT_PLAN.md for OR/PQ/HR/RF/OF/SF IDs, `A.U…`, U-unit names, lanes, LEAD
  NOTES, rounds and phases finds none. The two "lane" hits (CLAUDE.md:750, 754) are CI test lanes.
- Note (unchanged text): BACKLOG.md:75 and :223 cite "R9's other half", a hardware-queue label defined nowhere in the
  living text (PROJECT_AUDIT_PLAN.md:3282 explains it).
- The test labels F7/R9/R10 (tests/test_asy_isl29125_driver.py:573, 1619) are requirement numbers, per
  PROJECT_AUDIT_PLAN.md:3030.

## Outside the claims
1. **The dead-man's-switch recovery script restores nothing as written** (SPECIFICATION.md:2178-2192).
   - `97cc7496` ("No meaning change") replaced the validated `nmcli connection modify "Wired connection 1" …`/`up`
     lines with `"$PROFILE"`.
   - The script never assigns `$PROFILE`; only a comment says to read it. It is launched by `systemd-run …
     /bin/bash <script>`, which passes no such variable.
   - Copied as shown, the armed switch therefore runs `nmcli connection modify ""` and restores no connection.
   - B.13 still introduces it as "validated on a real successful run".
   - This is the reference script for a hard rule (CLAUDE.md:349-357).
2. The stale `asy_uart_comm.py`/`asy_uart_driver.py` line citations in SPECIFICATION.md:6701 (claim 3).
3. SPECIFICATION.md:10419 still calls Part K "the per-driver checklist" (claim 6 note).

How hard I tried:
- I read all of CLAUDE.md, old and new, side by side.
- I read Part 0, Part K, B.13, C.8's rule, E.2.2 and the new tests_hardware sections in full.
- I ran a word diff of the whole CLAUDE.md, a heading diff of three docs, and a scan of every added doc line for
  paths, file:line citations and history phrasing.
- I checked 26 owner tags against PROJECT_AUDIT_PLAN.md, the rulings file, audit/review and git history.
- I planted 9 breaks in 2 runs.
