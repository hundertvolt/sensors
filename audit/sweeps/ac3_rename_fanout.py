"""A-C3 Part S helper: for a rename action, list files at HEAD that use an old name but have no merged change carrying the action."""
import re, subprocess, sys
sys.path.insert(0, "audit/sweeps")
import ac3_fanout as fo
import ac3_site_trace as t

SCOPES = ["src", "buildgen", "js", "tests_js", "mockdata", "tests", "tests_scripts", "digital_twin", "tests_hardware", "scripts",
          "toolchain", ".github", "pyproject.toml", "host_typecheck.ini", "devices", "SPECIFICATION.md", "CLAUDE.md", "README.md",
          "BACKLOG.md", "DEVICE_REFERENCE.md", "UART_C_PORT_CHANGELOG.md", "THIRD_PARTY_LICENSES.md", "HEAP_FRAGMENTATION_MEASUREMENTS.md"]

def old_names(aid):
    a = {x["id"]: x for x in t.parse_actions()}[aid]
    txt = a["slots"].get("Site", "") + " " + a["slots"].get("Change", "")
    return sorted({m.group(1) for m in re.finditer(r"`([A-Za-z_][\w]*)`\s*(?:\([^)]*\)\s*)?(?:→|->)\s*`[A-Za-z_]", txt)})

if __name__ == "__main__":
    aid = sys.argv[1]
    names = sys.argv[2:] or old_names(aid)
    car = fo.carriers(aid)
    pat = r"\b(" + "|".join(map(re.escape, names)) + r")\b"
    out = subprocess.run(["git", "grep", "-lE", pat, "--"] + SCOPES, capture_output=True, text=True).stdout.split()
    miss = [f for f in out if not (car.get(f) or car.get(t.canon(f)))]
    print(aid, "names:", " ".join(names)[:600])
    print(len(out), "files use an old name;", len(miss), "without a carrier:")
    print("\n".join(miss))
