import sys, importlib.util, pathlib
sys.path.insert(0, "tests_scripts"); sys.path.insert(0, "tests_hardware")
spec = importlib.util.spec_from_file_location("bc", "tests_scripts/test_digital_twin_boot_contiguity.py")
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
from heap_map import parse_labelled
for f in sys.argv[1:]:
    t = pathlib.Path(f).read_text()
    m = parse_labelled(t)
    s, ab, al = m["batch_00"], m["after_batch"], m["after_starter_loop_end"]
    print(pathlib.Path(f).name, "batch: depth", -bc._median(s, ab), "reach", bc._reach(s, ab), "high", bc._blocks_above(s, ab, bc._HIGH_BAND),
          "| boot: depth", -bc._median(s, al), "reach", bc._reach(s, al), "high", bc._blocks_above(s, al, bc._HIGH_BAND),
          "| new batch B", len(bc._offsets_above_seam(s, ab)) * s.block_bytes, "| used", ab.used_bytes)
