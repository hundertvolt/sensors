
######## SubagentHandback 2026-10-13T21:15:16.780Z
U24 lane B hand-back. Commit d1c9d9c on audit/u24-b (based on 31d5bfc), not pushed. Logs are in S/u24/laneB/ (logs/, mypy_*.log, gen.prof).

**Steps: all 4 applied.**
1. **TomlDoc typed.** _toml_fixtures has no Any now. It adds checked accessors: table_at, array_at, instances, instance_of, table, array. All 6 consumers read through them, with no cast and no new `type: ignore`. A 1,930-finding host mypy run is now clean.
2. **Floors added.** The definitions loops at :238, :327, :480 and :716 and boot_contiguity :329 now run only on devices the TOMLs select (devices_with), and each selection has a floor test.
3. **Orphan modules.**
   - The generator removes every finished file it did not write, inside build/generated_src/ only; `.tmp` files stay.
   - The stamp now lists every file it writes, under a new "outputs" key.
   - require_fresh() refuses a tree whose files differ from that list.
4. **generate test sped up.** It now reads each real device's generation once through the cached `_real`, and shares one stripped src/ copy per driver set. No check was dropped.

**Deviations (agent, 2026-10-13):**
- TomlValue keeps buildgen's datetime members. The plan's literal left them out, but dict invariance needs the identical shape to pass fixture docs into buildgen.
- In error_contract, `_paired` is now `with_uart_pair()` (identical edits) and `_instance` is now `instance_of()`.
- I removed the two `type: ignore` at test_generated_tree:107-108 by narrowing.
- The guard also refuses a missing output and an empty outputs list.
- Test-file helpers keep their per-section placement (T's precedent).

**Seen failing first (on W1):**
- test_generated_tree.py:94: 3 orphan cases (module, plan, definitions) gave FRESH where STALE was expected.
- test_generated_tree.py:103: a missing output gave FRESH.
- test_generate_sensortask_modules.py:182: the removed device's files stayed.
- Floors: a plant that empties each selection turns the three floors red. W1's files under the same plants pass with everything skipped (19 and 6 skipped, rc 0).
- Bites (all went red): `.tmp` exclusion in the guard and in the generator; the 3 skip→assert changes (18 red); the ring-plan assert; the empty outputs list on my pre-fix variant.

**Red checks:**
- test_decision_vocabulary: one line is mine to retire, `tests_scripts/_decision_vocab_allowlist.txt:528`. The other 6 lines were already red on W1 (not mine).
- test_tunables_register (SPECIFICATION.md:10356-10357) and test_import_placement (stale _PENDING entries already stale at W1, from T's import moves): red at W1, no line mine.
- mypy main pass: 37 errors in 11 files, the same as F's wave-2 consumer list; none in my files.
- Clean: host pass, ruff, and the other 9 of the 12 checks.

**Baseline rows that retire:** host_typecheck.ini:41-42 `[mypy-_toml_fixtures]` and :65-66 `[mypy-test_buildgen_definitions]` (already retirable at W1). pyproject.toml: none.

**Generate profile:** 146 generate_device calls. Under cProfile, generate_device is 57.0 s of 63.6 s. Of that, frozen_modules.compute_frozen_modules is 49.0 s, and _collect_imports makes 11.8M recursive iter_child_nodes calls (an uncached re-walk on every call). build_model 7.5 s, ast.parse 5.3 s. Timed alone at nice 19: wall 24.7 s before (T's 27.4) → 12.3 s after; pytest's own time 20.8 s → 10.4 s.

**After-times** (seconds, wall; base from T):

| File | Base | After |
|---|---|---|
| generate | 27.4 | 12.3 |
| validate | 23.7 | 21.6 |
| definitions | 6.6 | 5.8 |
| fuzz | 10.2 | 8.1 |
| graph | 2.2 | 1.9 |
| pico_gpio | 1.0 | 0.8 |
| boot_contiguity | 14.3 | 13.9 |
| generate_sensortask_modules (grew, no base) | – | 9.9 |
| generated_tree (grew, no base) | – | 12.3 |

The 3 MicroPython files that import _generated_tree are green at -1, 32768 and settrace, with no memory errors. test_generated_boot_entry at 32768: 0.097–0.101 s against base 0.088, about 10 ms; a direct benchmark puts require_fresh within noise of W1's, about 10–13 ms per call for both.

**Scan:**
- Class 3, floors mode: covered by step 2.
- Class 4, stale-tree mode: covered by step 3.
- Class 3, new, fixed: the guard compared nothing when given an empty list (`tests/_generated_tree.py:23`).
- Class 4, new, not changed: the generator's suppressed `.tmp` unlink (`scripts/_generate_sensortask_modules.py:76`) is safe by construction, since a `.tmp` is never imported.
- New, not changed: two concurrent generator runs share `.tmp` names; this fails visibly with exit 1.

**Owed to X (SPECIFICATION.md L.4, L.5 and E.3):**
- The generator removes every file it did not write from build/generated_src (the top level, definitions/ and api/) before writing the stamps; `.tmp` files stay.
- `.inputs_stamp.json` is now `{"inputs", "outputs"}`, and "outputs" includes both stamps.
- require_fresh() refuses an orphan, a missing output or an empty list.
- New error line: `error: cannot remove <file>: <strerror>`, exit 1.

**Owed to the lead:**
- The two host_typecheck.ini rows and allow-list line :528 above.
- test_buildgen_error_contract.py takes 42 s wall but only 24.6 s of tests. The other 17 s is spent after the session tearing down 5.2M objects: buildgen/source_ast `_parse`'s lru_cache, keyed on (source, filename), holds 926 trees. Keying it on the text alone would share them; a SyntaxError is never cached, so the filename is not needed in the key.
- Caching compute_frozen_modules' per-file imports would cut the cost of every generate_device call.
- Website inputs: none.

**Owed to Y:** none.

**Runs:** every run exited as recorded in the logs. 2 lines in RUNS.md for the final batch (rc 0). Nothing of mine is running.
