"""A-C site index: parse every A-L action file into actions with their cited file sites, group by file."""
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACT = ROOT / "audit" / "actions"
SKIP = {"AC_NOTES.md", "REGISTER_FIXES_wave1.md", "REGISTER_FIXES_wave2.md", "REGISTER_FIXES_wave3.md"}
HEAD_RE = re.compile(r"^### (A\.[A-Za-z0-9]+\.[A-Za-z0-9]+)\b(.*)$")
SLOT_RE = re.compile(r"^- \*\*(Why|Site|Change|Blast|Depends|Kind)\*\*:\s?(.*)$")
PATH_RE = re.compile(r"`((?:src|buildgen|devices|digital_twin|tests|tests_scripts|tests_hardware|js|tests_js|html|scripts|toolchain|\.github|ext|datasheets)/[\w./\-]+|[A-Z_]+\.md|pyproject\.toml|package\.json|package-lock\.json|uv\.lock|eslint\.config\.js|\.nvmrc|tsconfig\.json)(?::[\d,\- ]+)?`")

def parse(path):
    acts, cur, slot = [], None, None
    for line in path.read_text().splitlines():
        m = HEAD_RE.match(line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2).strip(), "file": path.name, "slots": defaultdict(str)}
            acts.append(cur); slot = None; continue
        if cur is None:
            continue
        if line.startswith("## ") or line.startswith("### "):
            cur = None; continue
        s = SLOT_RE.match(line)
        if s:
            slot = s.group(1); cur["slots"][slot] += s.group(2); continue
        if slot and (line.startswith("  ") or line.startswith("\t")):
            cur["slots"][slot] += " " + line.strip()
    return acts

def main():
    acts = []
    for p in sorted(ACT.glob("*.md")):
        if p.name in SKIP:
            continue
        acts += parse(p)
    by_file = defaultdict(list)
    for a in acts:
        site_files = sorted({m.group(1) for m in PATH_RE.finditer(a["slots"].get("Site", ""))})
        a["site_files"] = site_files
        a["kind"] = a["slots"].get("Kind", "").strip()
        a["depends"] = sorted(set(re.findall(r"A\.[A-Za-z0-9]+\.[A-Za-z0-9]+", a["slots"].get("Depends", ""))))
        for f in site_files:
            by_file[f].append(a["id"])
    out = {"actions": [{k: v for k, v in a.items() if k != "slots"} for a in acts], "by_file": by_file}
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "audit" / "consolidation" / "site_index.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    nosite = [a["id"] for a in acts if not a["site_files"]]
    print(f"actions {len(acts)} · files {len(by_file)} · actions without a parsed file site {len(nosite)}")
    print("top files:", sorted(((len(v), k) for k, v in by_file.items()), reverse=True)[:25])
    print("no-site sample:", nosite[:40])

if __name__ == "__main__":
    main()
