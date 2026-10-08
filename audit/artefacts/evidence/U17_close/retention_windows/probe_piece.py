# Under the coverage runner: PieceBuffer rounds at 1x, 2x and 4x after warm-up, per measured kind; growth per run.
import gc
import test_asy_base_classes as t
for f in (t._written_and_copied_rounds, t._built_and_dropped_rounds, t._ambient_rounds):
    f(); f()
    out = []
    for reps in (1, 2, 4, 1, 2, 4):
        gc.collect(); b = gc.mem_alloc()
        for _ in range(reps):
            f()
        gc.collect(); out.append((reps, gc.mem_alloc() - b))
    print(f.__name__, out)
