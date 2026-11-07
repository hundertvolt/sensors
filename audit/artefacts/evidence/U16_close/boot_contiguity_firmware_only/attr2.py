# host side: every bound's metric computed on all new blocks and on the non-fake-log rest
import os, re, subprocess, sys
tree, probe = sys.argv[1], sys.argv[2]
arms = os.environ.get("ARMS", "collects suppressed").split()
sys.path.insert(0, os.path.join(tree, "tests_scripts")); os.chdir(tree)
import test_digital_twin_boot_contiguity as m
mp = "/root/pico-toolchain/micropython/ports/unix/build-standard/micropython"
def extents(kinds, heads):
    owned = set()
    for h in heads:
        if h < 0 or h >= len(kinds) or kinds[h] in ".=":
            continue
        owned.add(h); i = h + 1
        while i < len(kinds) and kinds[i] == "=":
            owned.add(i); i += 1
    return owned
for device in os.environ.get("DEVS", "wozi dev").split():
    for arm in arms:
        cfg = f"{os.path.dirname(os.path.abspath(probe))}/cfg_{device}_{arm}/"; os.makedirs(cfg, exist_ok=True)
        res = {}
        for pos in ("after_batch", "after_starter_loop_end"):
            c = subprocess.run([mp, "-X", f"heapsize={m._HEAPSIZE}", probe, device, arm, cfg, "0", pos], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
            r = m._checked_probe_run(device, arm, c)
            pool = r.pool_start; seam = r.maps["batch_00"]; bb = seam.block_bytes
            top = seam.total_bytes - seam.free_above_top_survivor
            after = r.maps[pos]
            heads = [(int(a, 16) - pool) // bb for a in re.findall(rf"^FAKE {pos} ([0-9a-f]+)$", c.stdout, re.M)]
            fake = extents(after.kinds, heads)
            new = [i for i, k in enumerate(after.kinds) if k != "." and seam.kinds[i] == "."]
            for name, sel in (("all", new), ("fw", [i for i in new if i not in fake])):
                offs = sorted(i * bb - top for i in sel)
                res[(pos, name)] = (len(offs), -offs[len(offs) // 2], offs[-1], sum(1 for o in offs if o > m._HIGH_BAND))
        for name in ("all", "fw"):
            n, bd, _, _ = res[("after_batch", name)]; n2, sd, reach, high = res[("after_starter_loop_end", name)]
            print(f"{device:9} {arm:10} {name:3} batch_n {n:5} batch_depth {bd:8} | boot_n {n2:5} boot_depth {sd:8} boot_reach {reach:8} high {high}", flush=True)
