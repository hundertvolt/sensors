# largest-free-run over free at after_batch and after_starter_loop_end, per probe, heap, device, arm
import os, subprocess, sys, statistics
tree = sys.argv[1]
sys.path.insert(0, os.path.join(tree, "tests_scripts")); os.chdir(tree)
import test_digital_twin_boot_contiguity as m
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
probes = {"fw_only": m._PROBE, "logs_kept": "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig2/probe_head.py"}
for spec in os.environ["RUNS"].split():
    device, heap, which = spec.split(":")
    for arm in ("suppressed", "collects"):
        rows = []
        for rep in range(int(os.environ.get("REPS", "1"))):
            cfg = f"/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u16/contig2/cfgl_{device}_{arm}/"; os.makedirs(cfg, exist_ok=True)
            c = subprocess.run([mp, "-X", f"heapsize={heap}", probes[which], device, arm, cfg, "0"], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
            try:
                r = m._checked_probe_run(device, arm, c)
            except AssertionError as e:
                print(device, heap, which, arm, "FAILED", str(e)[:300]); break
            ab, ae = r.maps["after_batch"], r.maps["after_starter_loop_end"]
            rows.append((ab.used_bytes * 100 / ab.total_bytes, ab.largest_free_run * 100 / ab.free_bytes, ae.largest_free_run * 100 / ae.free_bytes, ab.largest_free_run, ae.largest_free_run))
        if rows:
            f = lambda i: f"{min(x[i] for x in rows):.1f}-{max(x[i] for x in rows):.1f}"
            print(f"{device} {heap} {which:9} {arm:10} fill_ab {f(0)}% lf/free_ab {f(1)}% lf/free_end {f(2)}% largest_ab {statistics.median(x[3] for x in rows)} largest_end {statistics.median(x[4] for x in rows)}", flush=True)
