"""Throwaway review aid (PLAN.md section 2, step 4): marks each hunk of BASE..HEAD it proves mechanically.
RESTORED: its added lines are one contiguous run of the pre-audit or the post-U10 text of the same module; REMOVED:
a pure deletion of lines the audit added, every name it defined unreferenced at HEAD. The lead reads the rest."""
import re, subprocess, sys

PRE, U10 = "25caf528", "8d44fd14^"
DEF = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)|^\s*(_[A-Z][A-Z0-9_]*)\s*=\s*const\(")


def git(*a, ok=(0,)):
    p = subprocess.run(["git", *a], capture_output=True, text=True)
    if p.returncode not in ok:
        raise SystemExit(p.stderr)
    return p.stdout


def ref_lines(path):
    out = []
    for rev in (PRE, U10):
        for name in (path, path.replace("src/asy_", "src/")):
            t = git("show", f"{rev}:{name}", ok=(0, 128))
            if t:
                out.append([l.rstrip() for l in t.split("\n")])
                break
    return out


def contains(ref, run):
    n = len(run)
    return any(ref[i:i + n] == run for i in range(len(ref) - n + 1))


def main(base, head, paths):
    diff = git("diff", "-U0", "--no-renames", base, head, "--", *paths)
    files = re.split(r"^diff --git ", diff, flags=re.M)[1:]
    unmarked = 0
    for f in files:
        m = re.search(r"^\+\+\+ b/(\S+)", f, re.M) or re.search(r"^--- a/(\S+)", f, re.M)
        path = m.group(1)
        refs = ref_lines(path)
        for h in re.split(r"^@@ ", f, flags=re.M)[1:]:
            head_line, *body = h.split("\n")
            add = [l[1:].rstrip() for l in body if l.startswith("+") and not l.startswith("+++")]
            rem = [l[1:].rstrip() for l in body if l.startswith("-") and not l.startswith("---")]
            where = head_line.split(" @@")[0]
            verdict = "READ"
            if add and any(contains(r, add) for r in refs):
                verdict = "RESTORED"
            elif not add and rem and not any(contains(r, rem) for r in refs):
                names = [n for l in rem if DEF.match(l) for n in DEF.match(l).groups() if n]
                left = [n for n in names if git("grep", "-n", "-w", n, head, "--", ".", ":!audit", ":!arduino", ok=(0, 1))]
                verdict = "REMOVED" if not left else "READ (still referenced: " + ", ".join(left) + ")"
            if verdict.startswith("READ"):
                unmarked += 1
                print(f"{path} {where}: {verdict}, +{len(add)} -{len(rem)}")
    print(f"unmarked hunks: {unmarked}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or ["src", "buildgen"])
