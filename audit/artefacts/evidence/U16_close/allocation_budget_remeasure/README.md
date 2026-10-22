# FRAM allocation budget re-measured on the merged U16 tree

`measure.py` prices one blank and one valid `PrintLogHistoryStore.setup()` five times each in the budget test's own
collection-free window, on both Unix builds (`measure.log`). Medians: standard 25,952 B blank / 20,096 B valid
(was 28,864 / 20,512); settrace 262,656 / 238,144 (was 296,448 / 234,592). Spread: one run in five +480 B.
Budgets set ~15% above, never raised: standard 30,000 / 23,000 (was 34,000 / 24,000), settrace 302,000 (was
344,000) / 270,000 (kept: 13% above). CS-cycle counts unchanged (54 blank, 47 valid). Passes 3/3 at gc -1,
gc 32768 and under the coverage runner.
