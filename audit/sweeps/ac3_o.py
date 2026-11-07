"""A-C3 Part O helper: parse every merged change and run the adherence scans over their Change texts (read-only)."""
import collections, glob, json, re, sys

HEAD = re.compile(r"^### (M\.[A-Z_]+\.\d+)\b\s*(.*)$")
SLOT = re.compile(r"^- \*\*(From|Site|Change|Resolved|Unit|Depends|Blast carried by|Blast|Kind|Found while merging[^*]*)\*\*:\s?(.*)$")
QUOTED = re.compile(r"“([^”]{3,})”|\"([^\"]{3,})\"")
AUDIT_ID = re.compile(r"\bOR\d{1,3}\b|\b(?:G\d{1,2}|LEAD|REF)/R\d+|\bA\.(?:U\d|S0930|SDEP|C\.)|\bM\.[A-Z_]{3,}\.\d|\bV\.U\d|harmoni[sz]ation \d|AC_NOTES|\bRF\d{3}\b|\bHR\d{3}\b|\bPQ\d\b|\bAF-|PROJECT_AUDIT_PLAN|audit/(?:pass|actions|consolidation|hreq|refined|order)")
HISTORY = re.compile(r"\bused to\b|\bpreviously\b|\bformerly\b|\bno longer\b|\bwas found\b|\bbefore the fix\b|\ban earlier\b|\bthis audit\b|\bthe audit\b|\bwe (?:found|fixed)\b|\bhas been (?:fixed|removed|retired)\b", re.I)
NON_ASCII_WORD = re.compile(r"[A-Za-z]*[À-ɏ][A-Za-z]*")
CRED = re.compile(r"(?i)(password|passwd|token|secret|api[_ ]?key)\s*[=:]\s*[\"'][^\"'\s]{6,}[\"']")


def parse():
    ch = {}
    for f in sorted(glob.glob("audit/consolidation/M_*.md")):
        cur = slot = None
        path = None
        for line in open(f, encoding="utf-8"):
            if line.startswith("## "):
                path = line[3:].strip()
                cur = slot = None
                continue
            h = HEAD.match(line)
            if h:
                cur = h.group(1)
                ch[cur] = {"title": h.group(2), "file": f, "section": path, "slots": collections.defaultdict(str)}
                slot = None
                continue
            if not cur:
                continue
            s = SLOT.match(line)
            if s:
                slot = s.group(1)
                ch[cur]["slots"][slot] += s.group(2)
            elif slot and line.startswith("  "):
                ch[cur]["slots"][slot] += " " + line.strip()
            elif not line.strip():
                pass
            else:
                slot = None
    return ch


def quoted(text):
    for m in QUOTED.finditer(text):
        yield m.group(1) or m.group(2)


def scan(ch):
    out = collections.defaultdict(list)
    for k, c in ch.items():
        text = c["slots"].get("Change", "")
        for q in quoted(text):
            if AUDIT_ID.search(q):
                out["audit_id_in_quoted"].append((k, q[:300]))
            if HISTORY.search(q):
                out["history_in_quoted"].append((k, q[:300]))
            for w in NON_ASCII_WORD.findall(q):
                if len(w) > 2 and w not in ("µs", "°C"):
                    out["non_ascii_word"].append((k, w, q[:160]))
            if len(q) > 380 and re.search(r"header|docstring|comment", text[max(0, text.find(q) - 120):text.find(q)], re.I):
                out["long_comment"].append((k, len(q), q[:200]))
        for m in CRED.finditer(text):
            out["credential_like"].append((k, m.group(0)))
        site = c["slots"].get("Site", "")
        if re.search(r"`ext/(?!typings)", site):
            out["ext_site"].append((k, site[:200]))
        if re.search(r"`(?:python|modules|html_raw|legacy)/|`build-[a-z]+\.sh", site):
            out["legacy_site"].append((k, site[:200]))
        if re.search(r"control (?:arm|run)", text, re.I):
            out["control_arm"].append((k, text[:0] + re.search(r".{0,160}control (?:arm|run).{0,160}", text, re.I).group(0)))
        if re.search(r"commit message", text, re.I):
            out["commit_message"].append((k, re.search(r".{0,120}commit message.{0,200}", text, re.I).group(0)))
        if re.search(r"gc\.collect\(", text) and re.search(r"`src/|codegen", site):
            out["gc_collect_src"].append((k, re.search(r".{0,160}gc\.collect\(.{0,160}", text).group(0)))
        if "method-assign" in text and "src/" in site:
            out["method_assign_src"].append((k, site[:160]))
        for m in re.finditer(r"\((?:owner|agent|lead)[^)]{0,60}\)", text):
            tag = m.group(0)
            if not re.match(r"\((?:owner|agent|lead), \d{4}-\d{2}-\d{2}(?:, [^)]*)?\)$", tag) and re.search(r"\d{4}", tag):
                out["actor_tag_form"].append((k, tag))
    return out


def main():
    ch = parse()
    res = scan(ch)
    json.dump({k: {"title": v["title"], "file": v["file"], "section": v["section"], "slots": dict(v["slots"])} for k, v in ch.items()},
              open(sys.argv[1] if len(sys.argv) > 1 else "/dev/null", "w"), indent=0)
    for key, rows in res.items():
        print(f"== {key}: {len(rows)}")
        for r in rows:
            print("   ", " | ".join(str(x) for x in r))
    print("changes", len(ch))


if __name__ == "__main__":
    main()
