# The VOC gating duration is bounded by the algorithm itself

Question (owner, 2026-10-07): does Sensirion's C algorithm let `Gating_Duration_Minutes` grow without bound?
Source (`Sensirion/embedded-sgp` e9ecd60 `sensirion_voc_algorithm.c:574-587`, identical in `Sensirion/gas-index-algorithm`
2ef9f13 fixpoint `:630-644`): a plain int32 fix16 `+`, a clamp at 0, no upper clamp; past
`GATING_MAX_DURATION_MINUTES` (180) it zeroes `Uptime_Gating` every sample, which lifts the gating threshold back to its
initial 510 so the mean adapts again and the index falls - a feedback that bounds the duration.
Experiment (`exp.c`, `ramp.c`, gcc -O2, the C reference): the lowest valid raw value held for 400 days peaks at 182.95 min
(`run_20001.txt`); linear falls across the whole valid raw range (52767 -> 20001) over 0.02-100 days peak at 238.79 min,
with the index at 497 or above for at most 0.84 days (`ramp_results.txt`). The Python port reproduces the C reference to
the sample (`port_ramp.py`, 0.1-day ramp: 199.00 min at day 0.30, 25,611 samples at index >= 497, both). int32 overflow
(32,768 min) is unreachable by any input the chip can produce; were it reached, ISO C leaves signed overflow undefined and
GCC on ARM wraps, after which the clamp zeroes it. Result: no defect, no deviation from the literal port.
