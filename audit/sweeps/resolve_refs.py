"""DOC.T02 resolver: every `path:line`, SPECIFICATION `Part X.Y` and BACKLOG item citation in the living docs, at HEAD.
Prints each unresolved one as path<TAB>token<TAB>reason (feeds A.U0.08's allow-list); counts go to stderr.
Usage: resolve_refs.py [--code] [--sha SHA]  (--code also scans tracked code/config text; temporary, deleted with the audit)"""
import argparse
import collections
import re
import subprocess
import sys

from validate_plan import CONT_RE, REF_RE, numbers, resolver

SKIP_DIRS = ("audit/", "arduino/", "ext/", "datasheets/")
LEGACY = ("python/", "modules/", "html_raw/", "dev_legacy/", "build-", "update_and_install.txt")  # A.U0.08's pre-U1 exclusions
CODE_EXT = (".py", ".js", ".mjs", ".sh", ".toml", ".yml", ".yaml", ".ini", ".css", ".html", ".txt", ".cfg")
UPSTREAM_ROOTS = ("py", "ports", "extmod", "lib", "shared", "tools", "docs", "drivers")
PART_ID = r"[A-M](?:\.\d+)*"
KIND = {"beyond": "line out of bounds", "ambiguous": "ambiguous file name", "file": "missing file", "heading": "missing SPEC heading", "item": "missing BACKLOG item"}
# "Part C.7", "Parts A.4, C.7-C.9 and G", "Part F.5.8/F.5.9", "SPEC F.2", "SPECIFICATION.md's F.5" (list tail allowed).
PART_RE = re.compile(r"\b(?:Parts?|SPEC(?:IFICATION(?:\.md)?)?(?:'s)?(?:\s+Parts?)?)\s+(" + PART_ID + r"(?:\(\w+(?:\.\d+)?\))?"
                     r"(?:\s*(?:,|/|-|–|\band\b|\bor\b)\s*" + PART_ID + r"(?:\(\w+(?:\.\d+)?\))?)*)")
BARE_RE = re.compile(r"(?<![\w.§/#-])([A-M](?:\.\d+)+)(?![\w]|\.\d)")  # SPECIFICATION.md citing itself
BL_RE = re.compile(r"\bBACKLOG(?:\.md)?(?:'s)?(?:\s+own)?\s+(?:open\s+questions?|items?|#)\s*#?(\d+(?![-\d])(?:(?:\s*,\s*|/|\s+and\s+)#?\d+(?![-\d]))*)"
                   r"|\bBACKLOG(?:\.md)?\s+(\d+(?:/\d+)+)\b")
BL_SELF_RE = re.compile(r"\b(?:open\s+questions?|items?)\s+#?(\d+(?![-\d])(?:(?:\s*,\s*|/|\s+and\s+)#?\d+(?![-\d]))*)")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def spec_sections(spec):
    """SPEC heading ID -> (level, start, end) offsets; '# Part X' is level 1, '## X.Y' level 2 (code fences skipped)."""
    heads, pos, fence = [], 0, False
    for ln in spec.split("\n"):
        if ln.startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^(#{1,6}) (?:Part )?(" + PART_ID + r")\b", ln)
        if m:
            heads.append((m.group(2), len(m.group(1)), pos))
        pos += len(ln) + 1
    out = {}
    for i, (hid, lvl, start) in enumerate(heads):
        end = next((s for _h, lv, s in heads[i + 1:] if lv <= lvl), len(spec))
        out.setdefault(hid, (lvl, start, end))
    return out


def expand(ids_text):
    """'A.4, C.7-C.9 and G' -> ['A.4', 'C.7', 'C.8', 'C.9', 'G']; a '(e)'/'(f.1)' suffix names no heading of its own."""
    ids_text = re.sub(r"\(\w+(?:\.\d+)?\)", "", ids_text)
    out = []
    for item in re.split(r"\s*(?:,|/|\band\b|\bor\b)\s*", ids_text):
        rng = re.fullmatch(r"(" + PART_ID + r")\s*[-–]\s*(" + PART_ID + r")", item.strip())
        if rng and rng[1].count(".") == rng[2].count(".") > 0 and rng[1].rsplit(".", 1)[0] == rng[2].rsplit(".", 1)[0]:
            base, lo, hi = rng[1].rsplit(".", 1)[0], int(rng[1].rsplit(".", 1)[1]), int(rng[2].rsplit(".", 1)[1])
            out += [f"{base}.{n}" for n in range(lo, hi + 1)]
        elif rng:
            out += [rng[1], rng[2]]
        elif item.strip():
            out.append(item.strip())
    return out


def upstream(path):
    parts = path.split("/")
    return any(p in UPSTREAM_ROOTS for p in parts[:-1]) or path.startswith(("/", "$", "~"))


def scan(path, text, ctx, counts):
    bad = []
    for block in re.split(r"\n(?=\s*- |\s*\n|\|)", text):
        last = None
        for m in re.finditer(REF_RE.pattern + "|" + CONT_RE.pattern, block):
            if m.group(1):
                name, first, rest = m.group(1), m.group(2), m.group(3) or ""
                if block[max(0, m.start() - 1):m.start()] in (":", "^") or upstream(name):
                    last = None  # a <sha>:path citation names history, not HEAD; upstream sources live elsewhere
                    continue
                counts["path:line"] += 1
                last = ctx["resolve"](name)
                if last is None:
                    n_cands = len(ctx["by_base"].get(name.rsplit("/", 1)[-1], []))
                    bad.append((f"{name}:{first}", f"ambiguous file name ({n_cands} tracked files)" if n_cands > 1 and "/" not in name else "no such tracked file"))
                    continue
            elif last is not None:
                first, rest = m.group(4), m.group(5) or ""
                counts["path:line"] += 1
            else:
                continue
            size = ctx["size"](last)
            bad += [(f"{last}:{n}", f"line {n} beyond {size} lines") for n in numbers(first, rest) if not 1 <= n <= size]
    flat = " ".join(text.split())
    for m in PART_RE.finditer(flat):
        for pid in expand(m.group(1)):
            counts["Part"] += 1
            if pid not in ctx["heads"]:
                bad.append((f"Part {pid}", "no such heading in SPECIFICATION.md"))
    if path == "SPECIFICATION.md":
        for m in BARE_RE.finditer(flat):
            counts["Part"] += 1
            if m.group(1) not in ctx["heads"]:
                bad.append((m.group(1), "no such heading in SPECIFICATION.md"))
    for rx in (BL_RE, BL_SELF_RE) if path == "BACKLOG.md" else (BL_RE,):
        for m in rx.finditer(flat):
            for n in re.findall(r"\d+", m.group(1) or m.group(2)):
                counts["BACKLOG"] += 1
                if int(n) not in ctx["items"]:
                    bad.append((f"BACKLOG item {n}", "no such numbered item in BACKLOG.md"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", action="store_true", help="also scan tracked code/config text files, comments included")
    ap.add_argument("--sha", default="HEAD")
    a = ap.parse_args()
    sha, code = a.sha, a.code
    files = [f for f in git("ls-tree", "-r", "--name-only", sha).split("\n") if f and not f.startswith(SKIP_DIRS)]
    docs = [f for f in files if f.endswith(".md") and f != "PROJECT_AUDIT_PLAN.md"]
    if code:
        docs += [f for f in files if f.endswith(CODE_EXT) and not f.startswith(LEGACY)]
    sizes = {}

    def size(p):
        if p not in sizes:
            sizes[p] = git("show", f"{sha}:{p}").count("\n") + 1
        return sizes[p]

    backlog = git("show", f"{sha}:BACKLOG.md")
    by_base = collections.defaultdict(list)
    for f in files:
        by_base[f.rsplit("/", 1)[-1]].append(f)
    ctx = {"resolve": resolver(sha), "size": size, "by_base": by_base, "heads": spec_sections(git("show", f"{sha}:SPECIFICATION.md")),
           "items": {int(n) for n in re.findall(r"(?m)^(\d+)\. ", backlog)}}
    counts, seen, kinds = collections.Counter(), set(), collections.Counter()
    for f in docs:
        for token, reason in scan(f, git("show", f"{sha}:{f}"), ctx, counts):
            if (f, token) not in seen:
                seen.add((f, token))
                kinds[KIND[next(k for k in KIND if k in reason)]] += 1
                print(f"{f}\t{token}\t{reason}")
    print(f"{len(docs)} files at {sha}: {counts['path:line']} path:line, {counts['Part']} Part, {counts['BACKLOG']} BACKLOG citations; "
          f"{len(seen)} unresolved (path, token) pairs: " + ", ".join(f"{v} {k}" for k, v in kinds.most_common()), file=sys.stderr)


if __name__ == "__main__":
    main()
