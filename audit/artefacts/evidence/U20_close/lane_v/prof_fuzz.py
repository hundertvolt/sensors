import cProfile, pstats, sys, tempfile
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / "tests_scripts")]
import test_buildgen_fuzz as t
t._CASES = 300
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as d:
    cProfile.run("t.test_a_mutated_device_builds_or_fails_with_a_build_error(Path(d), root)", "fuzz.prof")
p = pstats.Stats("fuzz.prof"); p.sort_stats("cumulative").print_stats(25)
