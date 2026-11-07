import cProfile, pstats, sys, tempfile, time, importlib.util
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
cases = int(sys.argv[2])
sys.path[:0] = [str(repo), str(repo / "tests_scripts")]
spec = importlib.util.spec_from_file_location("fuzzmod", repo / "tests_scripts" / "test_buildgen_fuzz.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m._CASES = cases
with tempfile.TemporaryDirectory() as d:
    pr = cProfile.Profile(); t = time.perf_counter(); pr.enable()
    m.test_a_mutated_device_builds_or_fails_with_a_build_error(Path(d), repo)
    pr.disable(); print("wall", round(time.perf_counter() - t, 1), "s for", cases, "cases")
st = pstats.Stats(pr); st.sort_stats("cumulative")
st.print_stats(r"buildgen|tomllib/_parser.py:\d+\(loads\)|ast.py:\d+\(parse\)|tokenize.py:\d+\(_tokenize\)", 40)
