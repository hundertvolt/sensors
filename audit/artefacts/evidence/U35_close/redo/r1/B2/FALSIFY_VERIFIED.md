# B2 falsification: the lead's check of each refutation at the source (lead, 2026-11-03)

The falsifier (`FALSIFY.md`) refuted claims 3, 4, 6, 7, 9, 10, 11 and 12 of `FALSIFY_BRIEF.md`; 1, 2, 5, 8 and 13 (bytecode)
stand. Each refutation was read at the source; fixes go on `audit/r1-b2` (the unit agent, resumed with the list below).

| claim | refutation | verified | outcome |
|---|---|---|---|
| 3 | `rel_humidity()` uses b = 237.3 above 0 degC, pre-audit 237.4 | yes | the brief's wording: the constant is `abs_humidity()`'s, changed on the owner's word (2026-10-07: "Adapt the humidity to the verified range"); no fix |
| 4 | SCD30's config store logs W22 to a RAM-only logger | yes | the brief's wording: that logger is RAM-only by the owner's decision; no fix |
| 6 | with the tick refused, an uptime unread for 2**29 ms reads wrong | yes | stated limit, trigger refuted (V6); pre-audit uptime stopped counting then; comment fix (item 2) |
| 7 | a command accepted during a hung escalation entry rewrites the record to 9 | yes (gate checks `_reset_armed` only, :369) | fixed: the gate refuses once a reset is decided (item 1) |
| 9 | interleaved repeats of two codes take a slot each | yes (`_keep()` compares the newest entry only) | B2's removals hold for their own cases (one code per run); the owner kept the newest-entry rule (2026-11-03 06:41: "Keep as is.") |
| 10 | `fram_manager.py:671` and `uart_link_driver.py:290` read a `setup()` answer | yes | the brief's wording; the boot batch reads none; B3 keeps the FRAM driver's bool (`CARRY_LATER.md`) |
| 11 | a raising `_set_dict_cfg()` now answers 500, pre-audit ERR 100 | yes | kept as for the hook (`REVIEW.md`): a defect's path only, Microdot's catch and the hook log it |
| 12 | the storm bound, the generated-boot tolerance, `manual_persistence.py`, the erase-cut ring | yes (the planted SYSTEM warning passed) | fixed: items 4-7 |

Outside the claims: the mempause comment (fixed, item 2), ResetReason 9's catalog text and the BMP3XX comment (fixed,
item 3). The wet bulb above the dry bulb at the cold-dry corner (204 of 13,395 grid points; -20 degC, 5 %: -17.59
degC) is the owner's decision ("(a), remove the corner"), as at `25caf528`; stated in the report.
