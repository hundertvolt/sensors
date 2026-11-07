E2 hand-back (lane E, last block). Head e8b6f06 on audit/u35-e, on top of 8fb6241. Worktree S/wt-u35e. Nothing is uncommitted and nothing of mine is running. No src/ change, so there is no mpy-cross compare. Lane E is complete.

Commits:
- e507a88: step 39.
- d411724, be13031, bd9d811, e8b6f06: D.15 order for base_classes, isl, scd30 and bmp3xx. Each file has its own commit, and each is a pure move.

Steps by verdict:
- 39 applied. The snapshot test now reproduces the interleaving instead of only counting acquires. The device's get_bits() waits on an Event at its first call. A set_pressure_oversampling(8) started during that wait is shown not done. Once the gate opens:
  - the snapshot is (1, 1, 0);
  - the read pointers are [OSR, OSR, CONFIG, OSR];
  - the setter's OSR write is the last bus transaction;
  - the snapshot task acquired the session lock exactly once.
  The "can't be reproduced" comment is gone, and the new comment is the given text.
- D.15 applied in Q1's form: helpers in one sorted block; classes compared by their member multiset. For each file I checked the line multiset, the top-level AST node multiset and the docstring. C5's d15.py now prints "ok" for all four files. fram was already in order.
  - Q's import-time check also covers class-body method defaults (the LEAD NOTES 36 gap). It found nothing in these files.
  - base_classes: `_RaisingFramChunk.read_into` now comes before write_into.
  - bmp3xx: the two-paragraph fake-I2C note moves with `_register_reads` as one piece.
  - isl: the old over-long blank runs (one of 4 lines, two of 3) move with their lines. I did not change them, since changing them would be a content change.

Bites (scratch driver copies first on MICROPYPATH, deleted afterwards). Each fails only the new test:
- one session per field: "a write landed inside the snapshot: [28, 28, 28, 31]";
- no lock at all: "the setter wrote while the snapshot was parked between its field reads";
- the bus lock alone: the per-task acquire count fails (line 1464 at e507a88).

Decisions (agent, 2026-10-21):
- I could not read datasheets/bmp3xx/bst-bmp388-ds001.pdf. It is AES-256 encrypted, and this sandbox has no poppler or pypdf. So the comment on (1, 1, 0) does not repeat the step's "chip's reset encodings, DS001 Tables 34/36". It says these are the decoded zero bits of the fake's untouched registers.
- In base_classes, `_DividingReader` and `_ChipStoreReader` move up beside the file's other test doubles. Two moved helpers name them in unquoted annotations, and ruff gives F821 when such a helper sits above the class. Adding quotes would have been a content change.

Runs (one process at a time, all in unshare -n). Every log has zero MemoryError and zero "memory allocation failed":
- e2_checks39: head 138/138. The 3 bites gave rc=1 as planned.
- Paired base/head times in seconds, alternating, with 2-3 heavy processes on the host:

| File | gc -1 base/head | gc 32768 base/head |
|---|---|---|
| bmp3xx | 13.70/13.71 | 13.81/13.82 |
| scd30 | 22.25/22.08 | 28.29/28.59 |
| isl | 2.52/2.55 | 2.82/2.79 |
| base_classes | 0.41/0.37 | 0.42/0.44 |

  Every head run is green at both stages. bmp3xx and scd30 are both over 10 s at base, and neither grew.
- Before each of the 5 commits: ruff clean, both main mypy passes clean on a cold cache (264 and 131 files), and the 12 commit checks: 799 passed each time.
- E's complete checks: the 17 scans plus radio_shape_corpus in one process (883 passed), then test_microtest alone in unshare -n (24 passed). The only warning is the datasheets submodule one (test_citations.py:236).
- Each run has its start and done lines in RUNS.md.

Silent-failure scan of my 4 files, all classes: none found. The changes are test-only: STA, AP, Silent, Off and USB are unaffected on every device.

Facts owed:
- To the lead: the BMP3XX OSR reset value is contradictory between two files. tests/test_asy_bmp3xx_driver.py:1868 says 0x00 is "the chip's own reset values back". digital_twin/_bmp3xx_chip.py:41 has `_OSR_RESET = 0x02` from the DS001 register map. One of them needs the datasheet read on a machine that can decrypt the PDF. I did not edit either, because I had no source to ground the fix.
- To the lead: no allowlist row is orphaned and no tag changed. I wrote no relay lines.

Logs and tools are in S/u35/laneE/: e2_checks39.txt, e2_head39*.log, e2_bite39_*.log, e2_times.tsv, e2_t_*.log, e2_final*.log, pc_*.log; tools in e2tools/.