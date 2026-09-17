"""Tier-0 synthetic model for the heap-fragmentation defect (HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md
Part 2). Pure `gc` + `bytearray`, so the identical code runs in this model, in the digital twin and
on the real board - it models the MECHANISM, not the codebase."""

# Run under the MicroPython Unix port, never CPython:
#   micropython -X heapsize=400k tests/_heap_fragmentation_model.py
# The absolute numbers scale with -X heapsize; the ORDERING between scenarios is the result.

import gc

_PROBE_FLOOR = 256  # below this a "run" is allocator dust, not a usable region
_MAX_RUNS = 16


def largest_block(lo: int = 16, hi: int = 1 << 22) -> int:
    """Largest single contiguous allocation still obtainable - same probe shape as
    tests_hardware/device_scripts/heap_headroom_after_full_system_build.py's own _largest_block()."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            b = bytearray(mid)
            del b
            lo = mid
        except MemoryError:
            hi = mid - 1
    return lo


def free_run_profile(max_runs: int = _MAX_RUNS, floor: int = _PROBE_FLOOR) -> "list[int]":
    """Claim successively largest blocks and hold them; the sequence of sizes IS the free-run
    distribution. `largest_block()` alone cannot tell one big run from N medium ones - this can."""
    gc.collect()
    # Both lists are PRE-SIZED, and the claim is guarded. The handover's original sketch appended
    # to a growing list after claiming the largest run - so the append itself had to allocate out of
    # a heap whose biggest region had just been consumed, and the profiler MemoryError'd on its own
    # probe. Confirmed by running it. An instrument that dies on a fragmented heap is useless here,
    # since a fragmented heap is the only thing it is ever pointed at.
    held: list[bytearray | None] = [None] * max_runs
    prof = [0] * max_runs
    used = 0
    try:
        for i in range(max_runs):
            n = largest_block()
            if n < floor:
                break
            try:
                held[i] = bytearray(n)
            except MemoryError:
                break  # the run existed a moment ago; report what was measured, never raise
            prof[i] = n
            used = i + 1
    finally:
        held = []
        gc.collect()
    return prof[:used]


def churn(rounds: int = 200, size: int = 700) -> None:
    """Short-lived allocation. Models the bus/FRAM transaction traffic of the setup batch."""
    for _ in range(rounds):
        t = bytearray(size)
        del t


def interleaved(survivors: int = 12, rounds: int = 200) -> "list[bytearray]":
    """Models TODAY: a long-lived object born after each burst of churn, so survivors end up
    scattered across the whole heap and every gap between them bounds the largest free run."""
    kept = []
    for _ in range(survivors):
        churn(rounds)
        kept.append(bytearray(24))
    return kept


def survivors_first(survivors: int = 12, rounds: int = 200) -> "list[bytearray]":
    """Models the proposed __init__-before-setup() invariant: every long-lived object allocated in
    one churn-free phase, so they pack together and leave one contiguous region behind them."""
    kept = [bytearray(24) for _ in range(survivors)]
    for _ in range(survivors):
        churn(rounds)
    return kept


def churn_first(survivors: int = 12, rounds: int = 200) -> "list[bytearray]":
    """The control: all churn, then all survivors. Better than interleaved, worse than
    survivors-first - which is what rules out 'any separation will do'."""
    for _ in range(survivors):
        churn(rounds)
    return [bytearray(24) for _ in range(survivors)]


def measure(scenario: "str") -> "tuple[int, int, list[int]]":
    """Runs one scenario and returns (largest_block, mem_free, free_run_profile) with its survivors
    still alive - releasing them first would measure a heap the product never actually has."""
    builder = {"interleaved": interleaved, "survivors_first": survivors_first, "churn_first": churn_first}[scenario]
    gc.collect()
    kept = builder()
    # Collect BEFORE reading anything. This is the crux of the defect, not hygiene: on a
    # non-compacting collector dead churn coalesces, so a post-collect heap can only be fragmented
    # by SURVIVING objects at scattered addresses. Measuring pre-collect would report reclaimable
    # garbage as fragmentation and flatter the interleaved case. It also matches what the board's
    # own heap_headroom_after_full_system_build.py does.
    gc.collect()
    # free BEFORE largest_block(): the binary search leaves its own probe allocations behind as
    # uncollected garbage, so reading mem_free() afterwards understates it - enough to report the
    # impossible "largest > free". Order matters more than it looks here.
    free = gc.mem_free()
    largest = largest_block()
    profile = free_run_profile()
    del kept
    gc.collect()
    return largest, free, profile


def main() -> None:
    gc.collect()
    print(f"clean_heap largest={largest_block()} free={gc.mem_free()}")
    for scenario in ("interleaved", "survivors_first", "churn_first"):
        largest, free, profile = measure(scenario)
        print(f"{scenario} largest={largest} free={free} runs={len(profile)} profile={profile}")


if __name__ == "__main__":
    main()
