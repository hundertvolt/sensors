"""heapmap.py FILE: for each full map in a probe's console, the free-run histogram and object-kind counts."""
import collections, re, sys
lines = open(sys.argv[1], errors="replace").read().splitlines()
i = 0
while i < len(lines):
    m = re.match(r"HEAP (\S+) free (\d+) alloc (\d+)", lines[i])
    if not m: i += 1; continue
    j = i; body = []
    while j < len(lines) and not lines[j].startswith("HEAP_END"):
        k = re.match(r"([0-9a-f]{5,8}): (.*)$", lines[j])
        if k: body.append(k.group(2))
        j += 1
    if body:
        # a run of skipped all-free lines prints as "(N lines all free)"
        text = ""
        for l in lines[i:j]:
            k = re.match(r"([0-9a-f]{5,8}): (.*)$", l)
            if k: text += k.group(2).replace(" ", "")
            f = re.match(r"\s*\((\d+) lines all free\)", l)  # mem_info(1) indents these
            if f: text += "." * (int(f.group(1)) * 64)
        runs = [len(x) for x in re.findall(r"\.+", text)] or [0]
        hist = collections.Counter(min(r, 99) if r < 16 else (16 if r < 32 else 32 if r < 64 else 64 if r < 256 else 256) for r in runs)
        print(m.group(1), "free", m.group(2), "blocks", len(text), "free blocks", sum(runs), "largest run", max(runs), "(%d B)" % (max(runs) * 16), "runs", len(runs))
        print("  runs<16 blocks total", sum(r for r in runs if r < 16), "; >=16:", sorted((r for r in runs if r >= 16), reverse=True)[:12])
        print("  kinds", collections.Counter(c for c in text if c not in ".=").most_common(14))
        # head-size histogram
        objs = re.findall(r"([^.=])(=*)", text)
        sz = collections.Counter(); byk = collections.Counter()
        for h, t in objs:
            n = 1 + len(t); sz[n if n < 8 else 8 if n < 16 else 16 if n < 64 else 64 if n < 256 else 256] += n; byk[h] += n
        print("  blocks by object size (bucket: blocks)", sorted(sz.items()))
        print("  blocks by kind", byk.most_common(14))
    i = j + 1
