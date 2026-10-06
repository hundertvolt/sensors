import os, subprocess, sys, tempfile
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root / "tests_scripts"), str(root / "tests_hardware")]
import test_digital_twin_boot_contiguity as t
from heap_map import parse_labelled
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
for dev in sys.argv[2:]:
    for arm in sys.argv[1:2] and ("suppressed",):
        d = os.environ.get("CFGDIR") or tempfile.mkdtemp(); os.makedirs(d, exist_ok=True)
        c = subprocess.run([mp, "-X", "heapsize=16M", t._PROBE, dev, arm, d + "/", "0"], cwd=root,
                           env=dict(os.environ, MICROPYPATH=t._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, check=False)
        m = parse_labelled(c.stdout)
        s, ab, ae = m["batch_00"], m["after_batch"], m["after_starter_loop_end"]
        print(dev, arm, "batch_depth", -t._median(s, ab), "batch_reach", t._reach(s, ab), "batch_high", t._blocks_above(s, ab, t._HIGH_BAND),
              "boot_reach", t._reach(s, ae), "boot_depth", -t._median(s, ae), "boot_high", t._blocks_above(s, ae, t._HIGH_BAND),
              "n_new_boot", len(t._offsets_above_seam(s, ae)))
