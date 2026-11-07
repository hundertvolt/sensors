# Pass 4 merge — lead resolutions of the owner's answers (2026-09-29)

Input: `MERGE_INPUT.md` (Q01-Q45) and OR109. Everything not named here is applied as written.

## 1 Overrides

| Scan line | Treatment | Reason |
|---|---|---|
| Q29 (G7/R39) | applied; its "after question 2" part is M01 | answered, OR109.a (3) |
| Q30 (G3/R24 or BMP3xx interval block) | replaced by M02 | answered, OR109.a (2) |
| Q45 (new req near G3/R50) | becomes LEAD/R30, owner rank (lead) | OR109.a (0) |
| Q01-Q05, Q07, Q11, Q12, Q20 | applied by the lead | LEAD/REF blocks |

## 2 Lines created by the answers

- **M01 G7/R39** Rank, add: "ConfigManager errors keep their own rows (`CFGMGR_<name>`, '<module> Config Store') (owner, 2026-09-29, OR109.a (3)); the owner's 2026-09-16 'this chunking must be hidden' (`d4814cc`) reads as 'no FRAM chunk structure shown' (H.26)".
- **M02** the BMP3xx sample-interval block (G3/R24 if it carries the BMP3xx bound, else the block that does): Req or Rank, add: "`SampleInterv` stays 1-3,600 s, legacy's field-proven range and the ISL29125's (owner, 2026-09-29, OR109.a (2)); the 2026-07-22 '1-600 seconds' (`604c7bb`, reverted by `beaf97a`) is overtaken (H.10)".
- **M03 G3/R10** Req or State, add: "The fix16 helpers' per-sample temporary heap ints (≈ one SGP40 sample per second) are accepted: the GC reclaims them and nothing grows (owner, 2026-09-29, OR109.a (1)); no rework. The stored uptime values are state and follow LEAD/R24 (Q10, K.29)".
- **M04 G2/R17** State (with Q43): "the adapted `:356` test is LEAD/R30's regression test (owner, 2026-09-29, OR109.a (0))".
