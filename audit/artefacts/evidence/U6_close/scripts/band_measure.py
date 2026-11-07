import os, subprocess, sys
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root / "tests_scripts"), str(root / "tests_hardware")]
import test_digital_twin_boot_contiguity as t
from heap_map import parse_labelled
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
bands = [16, 24, 32, 48, 64, 96, 128]
arm = sys.argv[1]
for dev in sys.argv[2:]:
    d = f"/tmp/pytest-of-root/pytest-419/cfg_{dev}_{arm}0"; import shutil; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    c = subprocess.run([mp, "-X", "heapsize=16M", t._PROBE, dev, arm, d + "/", "0"], cwd=root,
                       env=dict(os.environ, MICROPYPATH=t._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, check=False)
    m = parse_labelled(c.stdout)
    s, ab, ae = m["batch_00"], m["after_batch"], m["after_starter_loop_end"]
    print(dev, arm, "boot", {b: t._blocks_above(s, ae, b * 1024) for b in bands}, "batch", {b: t._blocks_above(s, ab, b * 1024) for b in bands})
