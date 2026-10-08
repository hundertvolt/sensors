# Three retention tests judged one heap sample

The U17 gate's coverage leg (075d928) failed `test_piecebuffer_retains_nothing_after_construction` (32, 0) and
`test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat` (128 B). `probe_piece.py`: PieceBuffer rounds grow
exactly 0 in steady state on both binaries, one 32 B block toggling at a first sample. `probe_parts.py`, `probe_kind.py`,
`probe_trains*.py`: an apparent slow rise was the probes' own growing sample list (steps at the 5th and 9th append); with a
preallocated buffer the trains show +160 B within their first 100 rounds and then flat to 1,200 (`ws/` run). `probe_refuse.py`:
refusals alone grow 0 B even over 400; inside the test, sampling within a fresh `refusals()` coroutine read its own frame and
loop as 64 B every window, and the no-op control freed 64 B. `fix*_*.txt.gz`: the files after each step; `plants.py`: a
planted one-object-per-operation leak fails all three rewritten tests (1.5-4.2 KB a window).
