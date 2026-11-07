# The FRAM erase test's scaffolding refused by the coverage heap

`coverage_d58b8dd.log.gz`: the U16 re-gate's coverage leg, one failure: `test_erase_chip_zeroes_every_byte_in_ascending_units`
raising "memory allocation failed, allocating 16384 bytes" in its write recorder (a list of every write on the 256 KB
chip doubling). `fram_mgr_*.log.gz`: after the recorder became fixed counters, the settrace run refused the next block,
262144 bytes for the whole-chip zero comparison (standard binary 141/141 at both stages). `fram_mgr2_*.log.gz`: with the
zero check a 256-byte slice at a time, 141/141 on the settrace binary and at both GC stages, no allocation failure. A
planted descending erase (`range(size - unit, -1, -unit)` in `erase_chip()`) fails the rewritten test (df48814).
