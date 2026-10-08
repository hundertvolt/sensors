# U8C fix: the twin's 256KB FRAM could not be built under the coverage build

**Failure.** CI `unit-tests-coverage` on a47a1e6 (U8C), run 37561709046: `tests/test_digital_twin_bus_hazard_concurrency.py`'s
two dev tests failed in `build_system()` with `MemoryError: memory allocation failed, allocating 262144 bytes` at
`digital_twin/_fram_chip.py` `self.memory = bytearray(size)` (dev's 256KB MB85RS2MTA). The plain `unit-tests` jobs and
the local gate at both GC stages passed; only the settrace (coverage) build failed.

**Why U8C triggered it.** U8C changed that file only by naming its literals as module constants. `tests/microtest.py`
runs `test_*` functions in the order of the module's globals dict, a hash table on MicroPython, so seven new globals
reordered the file's twelve tests (`base_d38fceb_coverage_run.log` vs `u8c_2214141_coverage_run.log`: same tests,
different order). Deterministic: the base order passes 12/12, the U8C order fails the same two tests every run.

**Root cause: fragmentation, not a full heap.** The probe (`*_probe_free_heap.log`, `gc.mem_free()`/`mem_alloc()` just
before the allocation) shows the failing allocation with 14,963,264 bytes free of 16MB and 1,168,512 in use: no
contiguous 256KB run was left. The base order happened to build it (once with only 286,624 bytes free). MicroPython's GC
never moves live blocks, and the coverage build's inflated allocations leave small survivors scattered over the heap.

**Fix (design, not heap size).** The chip's memory is held in 4KB pages (`_PagedMemory`) that read and write like the
bytearray they replace; no allocation exceeds one page. A write past the chip's end is refused instead of silently
growing the chip. Tests first (`new_tests_against_the_old_chip.log`: the page test and the past-the-end test fail on the
old chip for their stated reasons; the bytearray-parity test passes on it, being the reference). After the fix the U8C
order passes 12/12 under the coverage build with zero memory errors (`fixed_coverage_run.log`).

Each log line is from the Unix-port settrace build (`build-settrace`, `-X heapsize=16M`) run alone in its own network
namespace; an earlier attempt that ran both revisions side by side failed one test on `EADDRINUSE` (the two runs sharing a
port), which is why each run is isolated.

**Full coverage suite on the fix** (`full_coverage_suite_summary.txt`, `scripts/test.sh --coverage` on a copy of the
fixed tree): all 88 MicroPython files pass under the settrace build, 3,872 tests, zero memory errors. Its pytest tier
counts 11 failures, every one `git ls-files -z` exiting 128 because that copy is not a git checkout; those files passed
in the unit's gate on the real worktree, and the fix touches none of what they read.
