# Pass 3 merge — lead ledger (LEAD.md, REF.md, owner rows)

- P015 | LEAD/R17 | applied | ruff global ignores naming a scope narrow to their files (C2.13's twelve listed)
- P029 | REF/R02 | applied | `error_log_helpers.py:49` and the unreachable `test_network_resilience.py:538` branch (sites checked at HEAD)
- P047 | REF/R05 | applied | dotted-quad check written twice (sites checked)
- P048 | REF/R02 | applied | `wlan_isconnected()` test-only caller (checked)
- P053 | LEAD/R10 | applied | password input unstyled (`html/style.css:261-263` checked)
- P057 | LEAD/R03 | applied | grkizi Run 5c SIGSEGV as a root-cause item
- P058 | LEAD/R12 | applied | runner argument validation (sites checked)
- P083 | LEAD/R29 | new requirement | owner source `2421948` checked
- P102 | LEAD/R25 | new requirement | owner source `144873f` checked
- P103 | LEAD/R26 | new requirement | owner source `d589d14` checked
- P104 | LEAD/R27 | new requirement | owner source `ef80090` checked
- P105 | LEAD/R28 | new requirement | owner source `8d77994` (items 15.12-15.14) checked
- OR101, OR104 (3), D4.36 | REF/R03 | applied | one never-UTC elapsed-time primitive in `base_classes.py`
- OR103, OR105 | LEAD/R24 | new requirement | no counter allocates or runs unbounded
- OR101-OR108 | LEAD.md section 1 row 16 | recorded | where each answer landed

Review of the agents' ledgers (A-E): every P and L part is recorded once; lead corrections after review:
OR70.a B04 (b) actor (E, `7c8dbbc`); G10/R03 cyw43 premise (E, N.74); G1/R02 D3 attribution narrowed (A, OR64).
Agent facts spot-checked and confirmed: MB85RS2MTA RP 18-80 kΩ and CS > VDD × 0.7 (B); `500851c` controlled-raise
wording (B); six `microdot` import suppressions and global `follow_imports` (D); `_cal_until_ms` bounded by the
120 s window and the 10 s NTP due check (C).
