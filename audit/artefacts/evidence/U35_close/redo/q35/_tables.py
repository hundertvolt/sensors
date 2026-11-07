"""Read-only: list the markdown tables in b3 records read from git show output, with header and row count."""
import subprocess
import sys

REPO, REF = sys.argv[1], sys.argv[2]
NAMES = sys.argv[3:]


def show(path):
    return subprocess.run(["git", "-C", REPO, "show", f"{REF}:{path}"], capture_output=True, text=True, check=True).stdout


def tables(text):
    lines = text.splitlines()
    out, i = [], 0
    section = ""
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("#"):
            section = ln.strip()[:70]
        if ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            header = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((i + 1, section, header, rows))
            i = j
            continue
        i += 1
    return out


if __name__ == "__main__":
    for name in NAMES:
        t = tables(show(f"audit/b3/{name}.md"))
        print(f"=== {name}: {len(t)} tables")
        for line, section, header, rows in t:
            print(f"  L{line} [{section}] rows={len(rows)} cols={header}")
