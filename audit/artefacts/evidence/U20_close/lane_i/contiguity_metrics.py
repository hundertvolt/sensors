"""Scratch: the boot-contiguity L0 file's figures for one probe log (live or suppressed arm)."""
import re, sys
sys.path.insert(0, sys.argv[1] + "/tests_hardware")
from heap_map import delta, parse_labelled

def offsets(before, after):
    ch = delta(before, after)
    seam_top = before.total_bytes - before.free_above_top_survivor
    return sorted(o * ch.block_bytes - seam_top for o in ch.new_offsets), ch.block_bytes

for path in sys.argv[2:]:
    text = open(path).read()
    maps = parse_labelled(text)
    seam = maps["batch_00"]
    b, bb = offsets(seam, maps["after_batch"])
    w, _ = offsets(seam, maps["after_starter_loop_end"])
    counters = dict(f.split("=") for m in re.finditer(r"^(?:LISTS|COUNTS) (.*)$", text, re.M) for f in m.group(1).split())
    rings = re.findall(r"^RING (\S+) (\S+) (\S+) (\d+)$", text, re.M)
    print(path.rsplit("/", 1)[-1], {
        "batch_median_depth": -b[len(b)//2], "batch_reach": b[-1], "batch_high": sum(1 for o in b if o > 32*1024),
        "batch_new_bytes": len(b) * bb,
        "boot_median_depth": -w[len(w)//2], "boot_reach": w[-1], "boot_high": sum(1 for o in w if o > 32*1024),
        "after_batch_used": maps["after_batch"].used_bytes,
        "largest_free_before": seam.largest_free_run, "largest_free_after_batch": maps["after_batch"].largest_free_run,
        "largest_free_after_loop": maps["after_starter_loop_end"].largest_free_run,
        "counters": counters, "rings": rings,
    })
