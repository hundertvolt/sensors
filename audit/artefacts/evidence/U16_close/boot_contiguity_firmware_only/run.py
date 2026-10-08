import os, subprocess, sys
tree, probe = sys.argv[1], sys.argv[2]
extra = sys.argv[3:]
sys.path.insert(0, os.path.join(tree, "tests_scripts"))
os.chdir(tree)
import test_digital_twin_boot_contiguity as m
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
devs = os.environ.get("DEVS", "wozi dev").split()
for device in devs:
    for arm in (m._ARM_LIVE, m._ARM_SUPPRESSED):
        cfg = f"/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig2/cfg_{device}_{arm}/"
        os.makedirs(cfg, exist_ok=True)
        c = subprocess.run([mp, "-X", f"heapsize={m._HEAPSIZE}", probe, device, arm, cfg, "0", *extra], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
        if os.environ.get("DUMP"):
            open(f"/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig2/out_{device}_{arm}.txt", "w").write(c.stdout)
        r = m._checked_probe_run(device, arm, c)
        mp_ = r.maps
        seam = mp_["batch_00"]
        offs = m._offsets_above_seam(seam, mp_["after_batch"])
        print(device, arm, "batch_depth", -m._median(seam, mp_["after_batch"]), "nnew", len(offs), "used_after_batch", mp_["after_batch"].used_bytes, "boot_depth", -m._median(seam, mp_["after_starter_loop_end"]), "boot_reach", m._reach(seam, mp_["after_starter_loop_end"]), "high", m._blocks_above(seam, mp_["after_starter_loop_end"], m._HIGH_BAND), flush=True)
