# every metric the test asserts, per device and arm, REPS times
import os, subprocess, sys
tree = sys.argv[1]
sys.path.insert(0, os.path.join(tree, "tests_scripts")); os.chdir(tree)
import test_digital_twin_boot_contiguity as m
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
for rep in range(int(os.environ.get("REPS", "1"))):
    for device in os.environ.get("DEVS", "wozi dev").split():
        for arm in os.environ.get("ARMS", "collects suppressed").split():
            cfg = f"/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig2/cfgm_{device}_{arm}/"; os.makedirs(cfg, exist_ok=True)
            c = subprocess.run([mp, "-X", f"heapsize={os.environ.get('HEAP', m._HEAPSIZE)}", m._PROBE, device, arm, cfg, "0"], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
            r = m._checked_probe_run(device, arm, c); M = r.maps; s = M["batch_00"]; ab = M["after_batch"]; ae = M["after_starter_loop_end"]
            nb = len(m._offsets_above_seam(s, ab)) * s.block_bytes
            print(f"{rep} {device:8} {arm:10} batch_new_B {nb:6} batch_depth {-m._median(s, ab):8} batch_reach {m._reach(s, ab):8} batch_high {m._blocks_above(s, ab, m._HIGH_BAND):4} | boot_depth {-m._median(s, ae):8} boot_reach {m._reach(s, ae):8} boot_high {m._blocks_above(s, ae, m._HIGH_BAND):4} used_ab {ab.used_bytes}", flush=True)
