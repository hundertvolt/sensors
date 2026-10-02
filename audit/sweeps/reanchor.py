"""Move `path:line` anchors in audit markdown from one commit to another, by the git diff between them.

Usage: reanchor.py OLD NEW FILE... [--dry]. Lines in unchanged regions shift; a line inside a changed hunk
or in a deleted file is reported (kept as is) for a manual look. Prints the report; exit 0.
"""

import re
import subprocess
import sys

EXT = r"py|md|sh|toml|js|mjs|json|yml|yaml|ini|txt|css|html|cfg"
REF = r"([\w./-]+\.(?:" + EXT + r")):(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)"
CONT = r"(?<=[\s(,`]):(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)(?![\d:])"
TOKEN = re.compile(REF + "|" + CONT)
UPSTREAM = ("py/", "extmod/", "ports/", "shared/", "lib/", "drivers/", "src/freezeFS.py")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


class Mapper:
    def __init__(self, old, new):
        self.old, self.new = old, new
        self.tracked = set(git("ls-tree", "-r", "--name-only", old).split("\n"))
        self.alive = set(git("ls-tree", "-r", "--name-only", new).split("\n"))
        self.changed = set(git("diff", "--name-only", old, new).split("\n")) - {""}
        self.by_base, self.hunks = {}, {}
        for t in self.tracked:
            self.by_base.setdefault(t.rsplit("/", 1)[-1], []).append(t)

    def resolve(self, p):
        if p in self.tracked:
            return p
        if p.startswith(UPSTREAM):
            return None
        cands = [c for c in self.by_base.get(p.rsplit("/", 1)[-1], []) if c.endswith("/" + p) or "/" not in p]
        src = [c for c in cands if c.startswith("src/")]
        return (src or (cands if len(cands) == 1 else []) or [None])[0]

    def map(self, path, n):
        """Return (new_n, problem or None)."""
        if path not in self.changed:
            return n, None
        if path not in self.alive:
            return n, "file deleted"
        if path not in self.hunks:
            hs = []
            for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", git("diff", "-U0", self.old, self.new, "--", path), re.M):
                a, b, c, d = int(m[1]), int(m[2] or 1), int(m[3]), int(m[4] or 1)
                hs.append((a, b, c, d))
            self.hunks[path] = hs
        shift = 0
        for a, b, c, d in self.hunks[path]:
            if b == 0:  # pure insertion after old line a
                if n > a:
                    shift += d
                continue
            if n < a:
                break
            if n <= a + b - 1:
                return c + min(n - a, max(d - 1, 0)), f"inside changed hunk -{a},{b} +{c},{d}"
            shift += d - b
        return n + shift, None


def rewrite_nums(mapper, path, spec, where, report):
    def one(m):
        n = int(m.group(0))
        new, prob = mapper.map(path, n)
        if prob:
            report.append(f"{where}: {path}:{n} -> {new}? ({prob})")
        return str(new)
    return re.sub(r"\d+", one, spec)


def process(mapper, fname, dry):
    text = open(fname, encoding="utf-8").read()
    report = []
    blocks = re.split(r"(\n(?=\s*- |\s*\n|\|))", text)
    out, lineno = [], 1
    for block in blocks:
        last = None

        def sub(m, lineno=lineno):
            nonlocal last
            where = f"{fname}:{lineno + m.string[: m.start()].count(chr(10))}"
            if m.group(1):
                last = mapper.resolve(m.group(1))
                if last is None:
                    return m.group(0)
                return m.group(1) + ":" + rewrite_nums(mapper, last, m.group(2), where, report)
            if last is None:
                return m.group(0)
            return ":" + rewrite_nums(mapper, last, m.group(3), where, report)

        out.append(TOKEN.sub(sub, block))
        lineno += block.count("\n")
    new = "".join(out)
    if not dry and new != text:
        open(fname, "w", encoding="utf-8").write(new)
    changed = sum(1 for a, b in zip(text.split("\n"), new.split("\n")) if a != b)
    return changed, report


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry"]
    mp = Mapper(args[0], args[1])
    total = []
    for f in args[2:]:
        c, rep = process(mp, f, "--dry" in sys.argv)
        print(f"{f}: {c} lines rewritten, {len(rep)} anchors to check")
        total += rep
    for r in total:
        print("  " + r)
