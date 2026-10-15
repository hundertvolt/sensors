# arms.py <tree>: both arms of the boot-contiguity probe for wozi and dev, with the check's own metrics.
import os, subprocess, sys
tree = sys.argv[1]
sys.path.insert(0, os.path.join(tree, "tests_scripts"))
os.chdir(tree)
import test_digital_twin_boot_contiguity as m
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
for device in ("wozi", "dev"):
    for arm in (m._ARM_LIVE, m._ARM_SUPPRESSED):
        cfg = f"/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig/cfg_{os.path.basename(tree)}_{device}_{arm}/"
        os.makedirs(cfg, exist_ok=True)
        c = subprocess.run([mp, "-X", f"heapsize={m._HEAPSIZE}", m._PROBE, device, arm, cfg, "0"], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
        r = m._checked_probe_run(device, arm, c)
        mp_ = r.maps
        seam = mp_["batch_00"]
        print(os.path.basename(tree), device, arm, "batch_depth", -m._median(seam, mp_["after_batch"]), "boot_depth", -m._median(seam, mp_["after_starter_loop_end"]), "boot_reach", m._reach(seam, mp_["after_starter_loop_end"]), "high", m._blocks_above(seam, mp_["after_starter_loop_end"], m._HIGH_BAND), flush=True)
