"""A-C3 Part S: trace every (action, Site file) pair to a merged change whose From names the action and whose Site names the file.

Corrected extractor (AC_NOTES 47): root files and directories, bare names continuing a Site list, SPEC abbreviations.
Writes audit/sweeps/ac3_site_trace.json; the findings are read by hand into audit/consolidation/AC3_S.md.
"""
import fnmatch, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACT = ROOT / "audit" / "actions"
CONS = ROOT / "audit" / "consolidation"
SKIP = {"AC_NOTES.md", "REGISTER_FIXES_wave1.md", "REGISTER_FIXES_wave2.md", "REGISTER_FIXES_wave3.md"}

FILES = {p for p in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
         if p and not p.startswith("arduino/")}
DIRS = {str(Path(p).parent) for p in FILES} | {"."}
for d in list(DIRS):
    while d not in (".", ""):
        DIRS.add(d); d = str(Path(d).parent)
TOP = {p.split("/")[0] for p in FILES} | {"legacy", "audit", "dev_legacy", "mockdata", "build", "typings", "html_raw", "datasheets"}
TOP -= {"arduino"}
EXT = r"(?:py|pyi|md|js|mjs|cjs|ts|json|toml|ini|sh|yml|yaml|txt|css|html|lock|ico|cmake|csv|svg|png|pdf|xml|c|h)"
BARE_RE = re.compile(r"^[\w<>*\-.]+\." + EXT + r"$")
TOKEN_RE = re.compile(r"[\w.<>*\-/]*\{[^{}\s`]*\}[\w.<>*\-/]*|[\w.<>*\-/]+")
SPEC_RE = re.compile(r"\bSPEC(?!IFICATION)\b(?=\s*(?:Part\s+)?[A-N](?:\b|\.\d))")
UPSTREAM = {"extmod", "ports", "py", "lib", "shared", "drivers", "mpy-cross", "micropython", "al"}
BASENAMES = defaultdict(list)
for _f in FILES:
    BASENAMES[_f.rsplit("/", 1)[-1]].append(_f)
LEGACY_PREFIXES = ("python/", "modules/", "dev_legacy/", "audit/actions/verify/")
ROOT_DOTFILES = {".gitignore", ".nvmrc", ".stylelintrc.json", ".htmlvalidate.json"}
# A.U10.37 renames: old and new src/ names count as one site (reported as an alias match).
RENAMED = ["api_response", "base_classes", "config_manager", "crc_checks", "framing_codecs", "print_log", "system_service", "captive_dns"]


# Site slots that say "the sites above"/"named last": the files their Why slot names (read by hand).
SITES_ABOVE = {
    "A.U26.45": ["tests_hardware/bench/test_network_resilience.py", "tests_hardware/conftest.py", "tests_hardware/isl29125_conformance.py",
                 "tests_hardware/flash/test_uart_crossover.py", "tests_hardware/manual/manual_sensor_accuracy.py"],
    "A.U26.65": ["tests_hardware/harness.py", "tests_hardware/bench_control.py", "tests_hardware/bench/test_hotspot_role_reversal.py",
                 "tests_hardware/bench/test_bus_concurrency_under_api_load.py", "tests_hardware/README.md"],
    "A.U26.69": ["tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py", "tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py"],
    "A.U26.76": ["tests_hardware/harness.py", "tests_hardware/error_log_helpers.py", "tests_hardware/http_client.py",
                 "tests_hardware/bench/test_uart_link_under_api_load.py", "tests_hardware/bench/test_bus_concurrency_under_api_load.py",
                 "tests_hardware/bench/test_sensor_config_push_over_real_hardware.py", "tests_hardware/device_scripts/allocation_need_per_source.py",
                 "tests_hardware/device_scripts/uart_crossover_exchange.py", "tests_hardware/device_scripts/uart_crossover_recovery.py"],
}


def tmatch(a, b):
    """A `<placeholder>` in either path matches any one path segment part."""
    if "<" not in a and "<" not in b:
        return False
    def rx(p):
        return "^" + re.sub(r"<[^>]*>", "[^/]+", re.escape(p)) + "$"
    return bool(re.match(rx(b), a) or re.match(rx(a), b))


def canon(p):
    for n in RENAMED:
        if p == f"src/asy_{n}.py":
            return f"src/{n}.py"
        if p == f"tests/test_asy_{n}.py":
            return f"tests/test_{n}.py"
    return p


def expand_braces(tok):
    m = re.search(r"\{([^{}]*)\}", tok)
    if not m:
        return [tok]
    out = []
    for alt in m.group(1).split(","):
        out += expand_braces(tok[:m.start()] + alt + tok[m.end():])
    return out


def exists(p):
    return p in FILES or p.rstrip("/") in DIRS


def ctx_dir(p):
    p = p.rstrip("/")
    return p if p in DIRS else str(Path(p).parent)


def extract(text, context=None):
    """Return [(path, how)] for every file/dir a Site text names. how: abs | rel | bare | bare-root | bare-new | spec | root."""
    out, ctx = [], context
    # a path broken across a line wrap inside backticks ("`tests/foo_ bar.py`") is rejoined
    text = re.sub(r"`[^`]*`", lambda m: re.sub(r"(?<=[_/\-]) (?=\w)", "", m.group(0)) if "/" in m.group(0) else m.group(0), text)
    ticked = set()
    for m in re.finditer(r"`([^`]*)`", text):
        ticked.update(range(m.start(), m.end()))
    for m in TOKEN_RE.finditer(text):
        raw, pos = m.group(0), m.start()
        for tok in expand_braces(raw):
            t = tok.rstrip(".,;:)(-").lstrip("(,;:-")
            if t.startswith("./"):
                t = t[2:]
            if "*" in t and "/" in t:
                hits = sorted(f for f in FILES if fnmatch.fnmatch(f, t))
                if hits:
                    out += [(h, "glob") for h in hits]; ctx = hits[-1]; continue
            if not t or re.fullmatch(r"[\d.\-]+", t):
                continue
            if "/" in t:
                first = t.split("/")[0]
                if not first or "//" in t or not t.strip("/"):
                    continue
                if first in UPSTREAM:
                    continue
                if first in TOP:
                    p = t.rstrip("/") if t.rstrip("/") in DIRS or not t.endswith("/") else t.rstrip("/")
                    p = t[:-1] if t.endswith("/") else t
                    out.append((p, "abs")); ctx = p; continue
                if ctx:
                    d = ctx_dir(ctx); hit = None
                    while True:
                        cand = t if d in (".", "") else f"{d}/{t}"
                        cand = cand.rstrip("/")
                        if exists(cand):
                            hit = cand; break
                        if d in (".", ""):
                            break
                        d = str(Path(d).parent)
                    if hit:
                        out.append((hit, "rel")); ctx = hit; continue
                    if pos in ticked and BARE_RE.match(t.split("/")[-1]):
                        d = ctx_dir(ctx)
                        while d not in (".", "") and f"{d}/{first}" not in DIRS:
                            d = str(Path(d).parent)
                        base = t if d in (".", "") else f"{d}/{t}"
                        out.append((base, "rel-new")); continue
                continue
            if t in ROOT_DOTFILES:
                out.append((t, "root")); continue
            if BARE_RE.match(t):
                if t.split(".")[0] in ("self", "e", "i", "os", "sys", "json", "time", "machine.mem_backup"):
                    continue
                if t in FILES:
                    out.append((t, "bare-root")); ctx = t; continue
                if ctx:
                    d = ctx_dir(ctx)
                    cand = t if d in (".", "") else f"{d}/{t}"
                    if exists(cand):
                        out.append((cand, "bare")); continue
                cands = BASENAMES.get(t, [])
                live = [c for c in cands if not c.startswith(LEGACY_PREFIXES)]
                if live and len(live) < len(cands):
                    cands = live
                if ctx:
                    sub = [c for c in cands if c.startswith(ctx_dir(ctx).split("/")[0] + "/")]
                    if len(sub) == 1:
                        out.append((sub[0], "bare-unique")); continue
                if len(cands) == 1:
                    out.append((cands[0], "bare-unique")); continue
                if len(cands) > 1:
                    out.append(("|".join(sorted(cands)), "bare-ambiguous")); continue
                if ctx:
                    out.append((f"{ctx_dir(ctx)}/{t}", "bare-new")); continue
                out.append((t, "bare-orphan")); continue
    for m in SPEC_RE.finditer(text):
        out.append(("SPECIFICATION.md", "spec"))
    for m in re.finditer(r"\bBACKLOG\b(?!\.md)", text):
        out.append(("BACKLOG.md", "prose-doc"))
    for m in re.finditer(r"(?<![/\w`])README\b(?!\.md)", text):
        out.append(("README.md", "prose-doc"))
    return out


def owner_cluster(f):
    """The cluster that owns a path (CLUSTERS.md lists, else by prefix)."""
    if f in CLUSTER_OF:
        return CLUSTER_OF[f]
    rules = [("tests_hardware/device_scripts", "HW_DEV"), ("tests_hardware/flash", "HW_DEV"), ("tests_hardware", "HW_BENCH"),
             ("tests/test_digital_twin", "TWIN"), ("digital_twin", "TWIN"), ("tests/test_", "TEST_UNIT"), ("tests/", "TEST_HELP"),
             ("tests_scripts", "TSC"), ("scripts", "SCR"), ("buildgen", "GEN"), ("devices", "GEN"), ("ext", "GEN"), ("html", "GEN"),
             ("js", "WEB"), ("tests_js", "WEB"), ("mockdata", "WEB"), ("toolchain", "TOOL"), (".github", "TOOL"), ("SPECIFICATION.md", "SPEC"),
             ("audit", "PROC"), (".gitignore", "PROC")]
    for pre, cl in rules:
        if f.startswith(pre):
            return cl
    return "DOCS" if f.endswith(".md") and "/" not in f else "?"


CLUSTER_OF = {}
_cl = None
for _line in (CONS / "CLUSTERS.md").read_text().splitlines():
    if _line.startswith("## "):
        _cl = _line[3:].split()[0]
    elif _cl:
        for _m in re.finditer(r"`([^`]+)`", _line):
            CLUSTER_OF.setdefault(_m.group(1).rstrip("/"), _cl)


def preambles():
    """A-IDs each M file's preamble (text before its first merged change) names: cluster-wide conventions."""
    out = {}
    for p in sorted(CONS.glob("M_*.md")):
        head = p.read_text().split("\n### M.", 1)[0]
        out[p.stem[2:]] = set(ids_in(head))
    return out


def parse_actions():
    head = re.compile(r"^### (A\.[A-Za-z0-9]+\.[A-Za-z0-9]+)\b(.*)$")
    slot = re.compile(r"^- \*\*(Why|Site|Change|Blast|Depends|Kind|Site\*\* and \*\*Change|Site and [Cc]hange)\*\*\s?(?:\([^)]*\))?:?\s?(.*)$")
    acts = []
    for p in sorted(ACT.glob("*.md")):
        if p.name in SKIP:
            continue
        cur = s = None
        for line in p.read_text().splitlines():
            m = head.match(line)
            if m:
                cur = {"id": m.group(1), "file": p.name, "slots": defaultdict(str)}; acts.append(cur); s = None; continue
            if cur is None:
                continue
            if line.startswith("## ") or line.startswith("### "):
                cur = None; continue
            sm = slot.match(line)
            if sm:
                s = "Site" if sm.group(1).startswith("Site") else sm.group(1)
                cur["slots"][s] += sm.group(2); continue
            if line.startswith("- **"):
                s = None; continue
            if s and (line.startswith("  ") or line.startswith("\t")):
                cur["slots"][s] += " " + line.strip()
    return acts


ID_RE = re.compile(r"\bA\.([A-Za-z0-9]+)\.([A-Za-z]?)(\d+)\b((?:\s*(?:/|,|-|–|and)\s*(?:A\.\1\.)?\.?[A-Za-z]?\d+\b(?!\.\d))*)")


def ids_in(text):
    """Every A-ID in a text, expanding A.U10.01-.05, A.U26.09/.32/.72, A.U15.R01-R03, A.U24.80-82."""
    out = []
    for m in ID_RE.finditer(text):
        unit, pre, num = m.group(1), m.group(2), m.group(3)
        width = len(num)
        out.append(f"A.{unit}.{pre}{num}")
        last = int(num)
        for sm in re.finditer(r"(/|,|-|–|and)\s*(?:A\.[A-Za-z0-9]+\.)?\.?([A-Za-z]?)(\d+)", m.group(4)):
            sep, n = sm.group(1), int(sm.group(3))
            w = max(width, len(sm.group(3)))
            if sep in "-–" and n > last and n - last < 200:
                out += [f"A.{unit}.{pre}{k:0{w}d}" for k in range(last + 1, n + 1)]
            else:
                out.append(f"A.{unit}.{pre}{n:0{w}d}")
            last = n
    return out


def parse_m():
    """Merged changes: id, cluster, heading files, slots; plus ledger rows per file."""
    head = re.compile(r"^### (M\.[A-Z_]+\.\d+)\b(.*)$")
    slot = re.compile(r"^- \*\*([A-Za-z ]+)\*\*:\s?(.*)$")
    changes, ledgers = [], []
    for p in sorted(CONS.glob("M_*.md")):
        cluster = p.stem[2:]
        sec_files, cur, s, in_ledger = [], None, None, False
        for line in p.read_text().splitlines():
            if line.startswith("## "):
                cur = None; s = None
                in_ledger = line.startswith("## Ledger")
                sec_files = [f for f, _ in extract(line[3:])]
                continue
            if in_ledger:
                if line.startswith("| A") or line.startswith("| SDEP") or line.startswith("| V."):
                    cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    if len(cells) >= 2:
                        ledgers.append({"cluster": cluster, "ids": ids_in(cells[0]) or [cells[0]], "text": " | ".join(cells[1:])})
                continue
            m = head.match(line)
            if m:
                cur = {"id": m.group(1), "cluster": cluster, "title": m.group(2).strip(), "sec_files": sec_files, "slots": defaultdict(str)}
                changes.append(cur); s = None; continue
            if cur is None:
                continue
            sm = slot.match(line)
            if sm:
                s = sm.group(1).strip(); cur["slots"][s] += sm.group(2); continue
            if line.startswith("- **"):
                s = None; continue
            if s and (line.startswith("  ") or line.startswith("\t")):
                cur["slots"][s] += " " + line.strip()
    return changes, ledgers


DROP_RE = re.compile(r"\b(dropped|drop|withdrawn|superseded|obsolete|void|not carried|no change|disposed|removed by|moot|stale|retired|already done|DONE at HEAD|no edit|holds)\b", re.I)


def main():
    acts = parse_actions()
    changes, ledgers = parse_m()
    for a in acts:
        a["sites"] = extract(a["slots"].get("Site", ""))
        if a["id"] in SITES_ABOVE:
            a["sites"] = [(f, "sites-above") for f in SITES_ABOVE[a["id"]]]
    by_from = defaultdict(list)
    for c in changes:
        c["from_ids"] = set(ids_in(c["slots"].get("From", "")))
        c["from_literal"] = set(re.findall(r"\bA\.[A-Za-z0-9]+\.[A-Za-z0-9]+\b", c["slots"].get("From", "")))
        c["body_ids"] = set(ids_in(" ".join(v for k, v in c["slots"].items() if k != "From")))
        site_txt = c["slots"].get("Site", "")
        ex = extract(site_txt, context=c["sec_files"][0] if c["sec_files"] else None)
        c["site_files"] = {canon(f) for f, _ in ex}
        explicit_first = bool(re.match(r"\s*`[^`]*/", site_txt)) or any(h in ("abs", "root", "bare-root", "spec") for _, h in ex)
        c["implicit"] = set()
        if c["sec_files"] and (not ex or re.match(r"\s*`?:\d", site_txt) or not explicit_first):
            c["implicit"] = {canon(f) for f in c["sec_files"]}
        for i in c["from_ids"]:
            by_from[i].append(c)
    ch_by_id = {c["id"]: c for c in changes}
    global PRE
    PRE = preambles()
    led = defaultdict(list)
    for r in ledgers:
        for i in r["ids"]:
            led[i].append(r)
    gaps_text = "\n".join((CONS / f"GAPS_G{k}.md").read_text() for k in range(1, 5))
    old_index = json.loads((CONS / "site_index.json").read_text())
    old_pairs = {(a["id"], f) for a in old_index["actions"] for f in a["site_files"]}
    pairs, rows = set(), []
    for a in acts:
        for f, how in a["sites"]:
            key = (a["id"], f)
            if key in pairs:
                continue
            pairs.add(key)
            cf = canon(f)
            cs = by_from.get(a["id"], [])
            exact = [c["id"] for c in cs if cf in c["site_files"]]
            impl = [c["id"] for c in cs if cf in c["implicit"]]
            # a directory site is carried by a change naming a file inside it, and vice versa
            nest = [c["id"] for c in cs if any(s.startswith(cf + "/") or cf.startswith(s + "/") for s in c["site_files"] | c["implicit"])]
            tmpl = [c["id"] for c in cs if any(tmatch(cf, s) for s in c["site_files"] | c["implicit"])]
            sitebody = [c["id"] for c in changes if (cf in c["site_files"] or cf in c["implicit"]) and a["id"] in c["body_ids"]]
            sect = [c["id"] for c in cs if cf in {canon(f) for f in c["sec_files"]}]
            own = owner_cluster(cf)
            conv = a["id"] in PRE.get(own, set())
            state = "exact" if exact else "implicit" if impl else "template" if tmpl else "section" if sect else "convention" if conv else "nested" if nest else "merged-elsewhere" if cs else "unmerged"
            rows.append({"action": a["id"], "unit_file": a["file"], "file": f, "how": how, "exists": exists(f),
                         "in_old_index": key in old_pairs, "state": state, "exact": exact, "implicit": impl, "nested": nest, "site_body": sitebody, "owner": own, "section": sect,
                         "range_only": bool(exact) and all(a["id"] not in ch_by_id[e]["from_literal"] for e in exact),
                         "from_changes": [c["id"] for c in cs],
                         "ledger": [f'{r["cluster"]}: {r["text"]}' for r in led.get(a["id"], [])],
                         "in_gaps": a["id"] in gaps_text,
                         "site_carriers": sorted({c["id"] for c in changes if cf in c["site_files"]})[:12]})
    out = {"actions": len(acts), "pairs": len(rows), "changes": len(changes), "rows": rows,
           "no_site": [a["id"] for a in acts if not a["sites"]]}
    dest = ROOT / "audit" / "sweeps" / "ac3_site_trace.json"
    dest.write_text(json.dumps(out, indent=1))
    from collections import Counter
    print("actions", len(acts), "pairs", len(rows), "changes", len(changes), "no-site actions", len(out["no_site"]))
    print("states", Counter(r["state"] for r in rows))
    print("how", Counter(r["how"] for r in rows))
    print("new pairs (not in old index)", sum(not r["in_old_index"] for r in rows),
          "old pairs missing now", len(old_pairs - pairs))


if __name__ == "__main__":
    main()
