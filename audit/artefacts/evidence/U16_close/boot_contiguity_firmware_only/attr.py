# host side: split each batch's new blocks into fake-log storage and the rest, and the median of each
import os, re, subprocess, sys
tree, probe = sys.argv[1], sys.argv[2]
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
    for arm in (m._ARM_LIVE, m._ARM_SUPPRESSED):
        cfg = f"{os.path.dirname(os.path.abspath(probe))}/cfg_{device}_{arm}/"; os.makedirs(cfg, exist_ok=True)
        c = subprocess.run([mp, "-X", f"heapsize={m._HEAPSIZE}", probe, device, arm, cfg, "0"], env=dict(os.environ, MICROPYPATH=m._MICROPYPATH, TZ="UTC"), capture_output=True, text=True, timeout=600, check=False)
        open(f"{os.path.dirname(os.path.abspath(probe))}/attr_{device}_{arm}.txt", "w").write(c.stdout + c.stderr)
        r = m._checked_probe_run(device, arm, c)
        pool = r.pool_start
        seam, after = r.maps["batch_00"], r.maps["after_batch"]
        bb = seam.block_bytes
        heads = [(int(a, 16) - pool) // bb for a in re.findall(r"^FAKE after_batch ([0-9a-f]+)$", c.stdout, re.M)]
        others = set(re.findall(r"^FAKEOTHER after_batch (.*)$", c.stdout, re.M))
        fake = extents(after.kinds, heads)
        top = seam.total_bytes - seam.free_above_top_survivor
        new = [i for i, k in enumerate(after.kinds) if k != "." and seam.kinds[i] == "."]
        nf = sorted(i * bb - top for i in new if i in fake); nr = sorted(i * bb - top for i in new if i not in fake)
        med = lambda xs: -xs[len(xs) // 2] if xs else None
        print(device, arm, "all", len(new), "depth", med(sorted(i * bb - top for i in new)), "| fake", len(nf), "depth", med(nf), "| rest", len(nr), "depth", med(nr), "reach", nr[-1] if nr else None, "others", others, flush=True)
