# N67: the owed test fixes and the register's per-file tag count (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneN/n67/`.
Sources: the verification tables `S/u35r/verify/V2.md` (rows 86, 88 and the notes under them), `V3.md` (row 92 and
item 1 of its list), `V5.md` (OF-13, OF-244), `audit/sweeps/open_findings.md` (OF-13, OF-16, OF-244). Re-locate every
line on your base and re-check each claim before you change anything. Every item is test, tool or register text only:
no `src/`, no generated file, no wear.

## Items
1. `tests/test_neopixel_wifi_integration.py:48` area: `test_real_neopixel_driver_on_off_toggle_through_wifi_service_ext_led`
   never sets up its `WifiService`; add `run(conn.setup())` the way the file's other tests set theirs up, from
   synchronous test scope (CLAUDE.md's nested `asyncio.run()` rule). Show what the test now exercises that it did not.
2. `tests/test_notification_scd30_integration.py:6` and `tests/test_notification_scd30_sgp40_integration.py:243` quote
   "each driver owns its own error log" as Part C.7's words; SPECIFICATION.md has no such phrase. Quote C.7 exactly
   (C.4's "each layer that meets the fault keeps its own entry (owner, 2026-10-02)" is the nearest) or drop the quotes.
3. `tests/test_notification_neopixel_integration.py:99-100`: the comment says freq=100 "keeps ramps fast in real
   wall-clock time", but the file runs on the driven clock; state why freq=100 is used now, or drop it if nothing holds.
4. `tests/test_ntp_fram_system_integration.py`, the three reader builders (`_make_bmp_reader`, `_make_scd30_reader`,
   `_make_sgp40_reader`, around :483-551): each resets its bus with `machine.I2C.reset_id(<bus>)` (tests/machine.py) so a
   NAK set cannot carry from one test into the next, and runs `run(reader.setup())` instead of `reader.cfgmgr.setup()`
   or nothing; pass `trigger_s=` where the file's other builders do. Every assertion kept.
5. OF-244: `tests_scripts/test_lint_ceilings.py` and `tests_scripts/test_ruff_exemptions_live.py` each carry a `_ruff()`;
   one shared helper (the tests_scripts helper modules first), both callers using it, both files green.
6. OF-13: `tests/test_asy_webserver_service.py`'s `_RUN_BOUND_S` (around :162) is a tuned bound with no `@tunable` tag;
   tag it with an ID named like the file's other two and add its Part N row (Basis as N.1 requires: measured from the
   file's runs at both stages, or estimated with the measurement owed). Check the file for other untagged tuned bounds.
7. OF-16: `tests_scripts/test_tunables_register.py` lists each file once per literal in a row's Sites cell, so deleting
   one of two same-literal tags of one ID in one file passes unseen. Extend Part N's Sites form (SPECIFICATION.md N.2,
   "The register's form") so a file carrying n >= 2 tags of the ID with that literal states n, and make the check
   compare the counts; update every row it then flags (about 16 file and ID pairs). Seen red first: with one of two
   tags deleted in a scratch copy, the check fails naming the file, ID and both counts. Decision tag
   "(agent, <date -u>)" on the form sentence.

## Proof and checks
Each changed MicroPython test file at both GC stages with the shared binary directly (TEST_DEVICE per device where the
file needs it), zero memory markers; where an item adds coverage, show it bite (a planted fault the old test missed).
ruff and the host mypy pass on changed Python; the comment cap, test_citations, test_decision_vocabulary,
test_tunables_register and every tests_scripts reader of a changed file. Your base has a changed `toolchain/`: no
`scripts/test.sh`, no twin CI, and nothing pointed at the shared toolchain that could rebuild it.

## Not yours
`src/`, `digital_twin/`, `toolchain/`, `scripts/`, audit/ records, every allow-list (hand back the row you need), the
NTP rows of Part N (another agent is changing them: if item 7 must touch one, hand it back). Commit subject
`U35 lane N67: <summary>`, the two trailers; do not push. Hand-back: commits, each item's red/green or why none, the
bites, anything for the docs with its line, the effect (test only, which devices); last line "nothing of mine is running".
