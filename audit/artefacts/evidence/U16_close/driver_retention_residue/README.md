# The UART driver's retention test: a per-run residue and a filling fake log, not a driver leak

The U16 gate on 37a88e6 failed `test_a_read_retains_nothing` once at gc -1 ((32, 0), `gate_37a88e6_gc_default.log.gz`);
eight serial file runs passed. `probe_retain.py` (the test alone, 20 calls per process) fails its first call in a fresh
process ((2752, 0)) and passes the other 19. `probe_warm.py` shows 128 B retained per read for the first ~30 reads after a
10-read warm-up and nothing after: `machine.mem32`'s 64-entry log (two register reads per read) still filling.
`probe_batches.py`/`probe_slope.py`: every `asyncio.run()` leaves a fixed residue (128 B for a no-op run, 192 B for a run
that used the UART), whatever its length, so the old one-run-against-one-control comparison judged residues.
`probe_lock.py`: 1,000 lock sections in one run leave the same 192 B - no per-transaction retention in the driver.
Fix (d722672): read until each capped fake log has wrapped once, then a 2,000-read run must grow the heap no more than a
1,000-read run; `probe_plant.py` (one 1-byte object kept per read) fails it at both GC stages ((144384, 79360)).
`load*.log`: the file at nice 19 against six nice-0 busy loops fails several wall-clock judgements (OF-33's class; at
equal priority, `eqload*.log`, it passes). `after*.log`, `final_*.log`: the file after the fix, 143/143 at both stages.
