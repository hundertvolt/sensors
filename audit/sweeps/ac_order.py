"""A-C2: step-level work-order parser over the merged changes (audit/consolidation/M_*.md).

A step is (change, unit). Run from the repo root: `python3 audit/sweeps/ac_order.py [--write]`.
"""
import collections
import glob
import json
import re
import sys

ROOT = "audit/consolidation"
OUT = "audit/order"

HEAD = re.compile(r"^### (M\.[A-Z_]+\.\d+)\b\s*(.*)$")
SLOT = re.compile(r"^- \*\*(From|Site|Change|Resolved|Unit|Depends|Blast carried by|Blast|Kind)\*\*:\s?(.*)$")
SEC = re.compile(r"^## (.*)$")

# ---- unit keys -------------------------------------------------------------------------------------
# B0 = the baseline (U0's first part), U0 = the rest of U0, U0R = U0's dependency refresh (LEAD/R33),
# U1..U37 with U8C, U8C2 after U8, then C (phase C), D (phase D).
UNITS = ["B0", "U0", "U0R"] + [f"U{i}" for i in range(1, 9)] + ["U8C", "U8C2"] + [f"U{i}" for i in range(9, 38)] + ["C", "D"]
UIDX = {u: i for i, u in enumerate(UNITS)}


def ukey(u):
    return UIDX[u]


# ---- action index ----------------------------------------------------------------------------------
def load_actions():
    d = json.load(open(f"{ROOT}/site_index.json"))
    acts = {a["id"]: a for a in d["actions"]}
    canon = {}
    for a in acts:
        p, n = re.match(r"A\.([A-Za-z0-9]+)\.([A-Za-z]?\d+)$", a).groups()
        m = re.match(r"([A-Za-z]?)(\d+)$", n)
        canon[(p, m.group(1), int(m.group(2)))] = a
    return acts, canon


# Supplement SUPP_owner_0930 actions: the unit its text states (ledger table, SUPP_owner_0930.md:1748-1762 and the
# per-action Why/State lines). Tests whose Depends name U24 actions land in U24 (L0/L1), U25 (L2), U26 (L3/L4).
S0930_UNIT = {
    1: "U20", 2: "U20", 3: "U24", 4: "U25", 5: "U26", 6: "U26", 7: "U36", 8: "U36", 9: "U19", 10: "U20", 11: "U20",
    12: "U11", 13: "U11", 14: "U11", 15: "U11", 16: "U11", 17: "U16", 18: "U19", 19: "U24", 20: "U24", 21: "U24",
    22: "U24", 23: "U24", 24: "U24", 25: "U24", 26: "U24", 27: "U25", 28: "U26", 29: "U26", 30: "U36", 31: "U11",
    32: "U11", 33: "U11", 34: "U24", 35: "U24", 36: "U24", 37: "U24", 38: "U25", 39: "U26", 40: "U26", 41: "U36",
}


def action_unit(aid):
    p, n = re.match(r"A\.([A-Za-z0-9]+)\.([A-Za-z]?\d+)$", aid).groups()
    if p == "C":
        return "C"
    if p == "SDEP":
        return "U37" if aid == "A.SDEP.25" else "U0R"
    if p == "S0930":
        return S0930_UNIT[int(n)]
    m = re.match(r"U(\d+)(C2|C)?[ab]?$", p)
    return f"U{m.group(1)}{m.group(2) or ''}"


# ---- ID expansion ----------------------------------------------------------------------------------
AFULL = re.compile(r"A\.([A-Za-z0-9]+?)\.([A-Za-z]?)(\d+)")
ACONT = re.compile(r"^(\s*(?:/|,|-|–|and|to)\s*)(?:A\.([A-Za-z0-9]+?)\.)?\.?([A-Za-z]?)(\d+)\b(?!\.\d)")
MFULL = re.compile(r"M\.([A-Z][A-Z_]*[A-Z])\.(\d+)")
MCONT = re.compile(r"^(\s*(?:/|,|-|–)\s*)(?:M\.([A-Z][A-Z_]*[A-Z])\.|\.)(\d+)\b")


def expand_a(text, canon, unknown=None):
    """Ordered list of (aid, start, end) for every A-ID in text, abbreviations and ranges expanded."""
    out = []
    pos = 0
    while True:
        m = AFULL.search(text, pos)
        if not m:
            break
        p, let, num = m.group(1), m.group(2), int(m.group(3))
        start, end = m.start(), m.end()
        ids = [(p, let, num)]
        while True:
            c = ACONT.match(text[end:])
            if not c:
                break
            sep = c.group(1).strip()
            p2 = c.group(2) or p
            let2, num2 = c.group(3), int(c.group(4))
            if p2 != p and not c.group(2):
                break
            # a bare continuation must carry the leading dot ("/.42", ", .06", "-.17")
            if not c.group(2) and not text[end:].lstrip()[len(sep):].lstrip().startswith(".") and not (let2 and let2 == let):
                break
            if sep in ("-", "–", "to") and p2 == p and let2 == let:
                for k in range(num + 1, num2 + 1):
                    if (p, let, k) in canon:
                        ids.append((p, let, k))
            else:
                ids.append((p2, let2, num2))
            p, let, num = p2, let2, num2
            end += c.end()
        for t in ids:
            if t in canon:
                out.append((canon[t], start, end))
            elif unknown is not None:
                unknown.append(f"A.{t[0]}.{t[1]}{t[2]}")
        pos = end
    return out


def expand_m(text):
    out = []
    pos = 0
    while True:
        m = MFULL.search(text, pos)
        if not m:
            break
        cl, num = m.group(1), int(m.group(2))
        start, end = m.start(), m.end()
        ids = [(cl, num)]
        while True:
            c = MCONT.match(text[end:])
            if not c:
                break
            sep = c.group(1).strip()
            cl2, num2 = c.group(2) or cl, int(c.group(3))
            if sep in ("-", "–") and cl2 == cl and num2 > num and num2 - num < 60:
                ids.extend((cl, k) for k in range(num + 1, num2 + 1))
            else:
                ids.append((cl2, num2))
            cl, num = cl2, num2
            end += c.end()
        out.extend((f"M.{a}.{b:03d}", start, end) for a, b in ids)
        pos = end
    return out


# ---- M-file parser ---------------------------------------------------------------------------------
def parse():
    ch = {}
    for f in sorted(glob.glob(f"{ROOT}/M_*.md")):
        cur = slot = None
        sec = None
        for ln, line in enumerate(open(f), 1):
            h = HEAD.match(line)
            if h:
                cur = h.group(1)
                ch[cur] = {"title": h.group(2).strip(), "file": f, "line": ln, "section": sec,
                           "slots": collections.defaultdict(str), "slot_line": {}}
                slot = None
                continue
            s2 = SEC.match(line)
            if s2:
                sec = s2.group(1).strip()
                cur = slot = None
                continue
            if not cur:
                continue
            s = SLOT.match(line)
            if s:
                slot = s.group(1)
                ch[cur]["slots"][slot] += s.group(2)
                ch[cur]["slot_line"].setdefault(slot, ln)
            elif slot and line.startswith("  ") and line.strip():
                ch[cur]["slots"][slot] += " " + line.strip()
            elif not line.strip():
                pass
            else:
                slot = None
    return ch


# ---- From slot: constituents and whether each one edits ---------------------------------------------
NONLIVE_START = re.compile(r"^\s*(read\b|holds?\b|hold\b|dropped\b|withdrawn\b|superseded\b|obsolete\b|void\b|blast-only\b|"
                           r"DONE-AT-HEAD\b|not written\b|never lands\b|no edit\b|no change\b)", re.I)
NONLIVE_END = re.compile(r"(?:^|[,;:]\s*)(superseded|dropped|withdrawn|obsolete|void|holds?)\s*\.?\s*$", re.I)
GROUP_Q = re.compile(r"(?:^|[;.]\s+|\s)(read|dropped(?: constituents)?(?: \([^)]*\))?|superseded|withdrawn|"
                     r"blast-only(?:, holds?)?|holds?)\s*:", re.I)


SUBPART = re.compile(r"(\d+[a-z]?|[a-h]|[ivx]+)( ?[-–,/] ?(\d+[a-z]?|[a-h]|[ivx]+))*")


def paren_after(text, i):
    """The balanced parenthetical starting at text[i:] after optional spaces, sub-part markers skipped."""
    j = i
    texts = []
    while True:
        k = j
        while k < len(text) and text[k] == " ":
            k += 1
        if k >= len(text) or text[k] != "(":
            break
        depth = 0
        for e in range(k, len(text)):
            if text[e] == "(":
                depth += 1
            elif text[e] == ")":
                depth -= 1
                if depth == 0:
                    break
        inner = text[k + 1:e]
        texts.append(inner)
        j = e + 1
        if not SUBPART.fullmatch(inner):  # "(2)", "(1)(3)", "(a)" sub-part markers: keep looking
            break
    return " ".join(t for t in texts if not SUBPART.fullmatch(t)) or ""


def from_constituents(text, canon, unknown):
    """[(aid, live)] for the From slot."""
    res = []
    # segments split at top-level ';'
    segs, depth, startp = [], 0, 0
    for i, c in enumerate(text):
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif c == ";" and depth == 0:
            segs.append((startp, text[startp:i]))
            startp = i + 1
    segs.append((startp, text[startp:]))
    for off, seg in segs:
        q = None
        for g in GROUP_Q.finditer(seg):
            # a qualifier only counts at top level of the segment
            pre = seg[:g.start()]
            if pre.count("(") == pre.count(")"):
                q = g.end()
                break
        for aid, s, e in expand_a(seg, canon, unknown):
            pre = seg[:s]
            if pre.count("(") > pre.count(")"):
                continue  # an ID inside another constituent's parenthetical is a reference, not a constituent
            par = paren_after(seg, e)
            live = True
            if q is not None and s >= q:
                live = False
            if par and (NONLIVE_START.search(par) or NONLIVE_END.search(par)):
                live = False
            res.append((aid, live, par[:160]))
    return res




# ---- action files: Site and Depends with context -----------------------------------------------------
PATHTOK = re.compile(r"`([^`\s]+?)(?::[\d,\- ]+)?`")
PATHLIKE = re.compile(r"^(?:[\w.-]+/)*[\w.-]+\.(?:py|md|js|mjs|json|toml|ini|sh|yml|yaml|txt|css|html|lock|cfg|d\.ts|uf2)$|"
                      r"^(?:[\w.-]+/)+$|^\.(?:nvmrc|gitignore)$|^(?:mockdata|dev_legacy|legacy|audit|ext|datasheets)/")


def paths_in(text):
    out = set()
    for m in PATHTOK.finditer(text):
        p = m.group(1).rstrip(".,;")
        p = re.sub(r":\d.*$", "", p)
        if PATHLIKE.search(p) and not p.startswith(("http", "A.", "M.")):
            out.add(p)
    return out


def load_action_slots():
    sys.path.insert(0, "audit/sweeps")
    import ac_index
    from pathlib import Path
    acts = {}
    for p in sorted(Path("audit/actions").glob("*.md")):
        if p.name in ac_index.SKIP:
            continue
        for a in ac_index.parse(p):
            acts[a["id"]] = a
    return acts


# ---- Unit slot tokens --------------------------------------------------------------------------------
UTOK = re.compile(r"(?<![A-Za-z0-9.])(U\d+(?:C2|C)?|B0|phase [CD]|S0930)(?:[ab])?\b")


def unit_tokens(text, cons):
    """Units the Unit slot names as landing units (main first), IDs and code spans removed; 'after Ux' is a reference."""
    t = re.sub(r"`[^`]*`", "", text)
    t = AFULL.sub("A.ID", t)
    t = MFULL.sub("M.ID", t)
    out = []
    for m in UTOK.finditer(t):
        pre = t[max(0, m.start() - 9):m.start()].lower()
        if re.search(r"(after|before|from|until|since|not)\s+$", pre):
            continue
        tok = {"phase C": "C", "phase D": "D", "B0": "U0"}.get(m.group(1), m.group(1))
        if tok == "S0930":
            out.extend(sorted({action_unit(a) for a, live, _ in cons if a.startswith("A.S0930")}, key=ukey))
            continue
        out.append(tok)
    return out


def norm_unit(u):
    return "U0" if u == "B0" else u


# U0R is U0's dependency-refresh step (LEAD/R33): after the B0 baseline, before U1. M files name it "U0".
UNITS = [u for u in UNITS if u != "B0"]
UIDX = {u: i for i, u in enumerate(UNITS)}


# ---- action-level dependencies (each action's Depends slot, abbreviations expanded) -------------------
REV = re.compile(r"follow it\b|take the results|decides the shape|land later|execute later|append their own|"
                 r"is this action|follows? this|^\W*before\s*$", re.I)
CO = re.compile(r"co-land|A-C merges|A-C keeps|A-C moves|same (?:function|file|site|line|bullet|section|table|test|class|"
                r"block|lines|sentence|paragraph|row|module|helper|method|constant|loop|guard|rule|commit|getters|"
                r"`|shape|contract|entry|class)", re.I)
IGN = re.compile(r"withdrawn|superseded|conflicts? with", re.I)


def action_deps(S, canon):
    """{a: [(b, cls)]}: cls 'order' (b first), 'co' (lands with b), 'rev' (b follows a), 'ign' (no ordering)."""
    out = {}
    for aid, a in S.items():
        d = a["slots"].get("Depends", "")
        segs, depth, st = [], 0, 0
        for i, c in enumerate(d):
            if c == "(":
                depth += 1
            elif c == ")":
                depth = max(0, depth - 1)
            elif c == ";" and depth == 0:
                segs.append(d[st:i])
                st = i + 1
        segs.append(d[st:])
        res = []
        for seg in segs:
            for b, s, e in expand_a(seg, canon):
                if b == aid:
                    continue
                around = seg[max(0, s - 60):e] + paren_after(seg, e)
                tail = seg[e:]
                if IGN.search(paren_after(seg, e)) or re.search(r"conflicts? with\s*$", seg[max(0, s - 20):s], re.I):
                    cls = "ign"
                elif (REV.search(seg[e:e + 60]) or REV.search(paren_after(seg, e)) or REV.search(seg[max(0, s - 40):s])
                      or re.search(r"\bbefore\s+$", seg[max(0, s - 12):s])):
                    cls = "rev"
                elif CO.search(around) or CO.search(seg[e:e + 80]) or re.search(r"A-C merges", tail[:200]):
                    cls = "co"
                else:
                    cls = "order"
                res.append((b, cls))
        out[aid] = res
    return out


# ---- the step model ----------------------------------------------------------------------------------
def heading_paths(sec):
    out = set()
    for tok in re.split(r"[,\s]+", sec or ""):
        tok = tok.strip("`()")
        if PATHLIKE.search(tok):
            out.add(tok)
    return out


def fkey(p):
    """Compare site files across the U10 module renames: basename without an `asy_` prefix, plus the directory."""
    d, _, b = p.rstrip("/").rpartition("/")
    return (d, re.sub(r"^asy_", "", b))


def build():
    acts, canon = load_actions()
    S = load_action_slots()
    D = action_deps(S, canon)
    ch = parse()
    unknown = []
    act_files = {a: {fkey(p) for p in paths_in(S[a]["slots"].get("Site", ""))} for a in S}
    for k, c in ch.items():
        c["cons"] = from_constituents(c["slots"]["From"], canon, unknown)
        c["live"] = [a for a, live, _ in c["cons"] if live and k not in NOSTEP]
        toks = unit_tokens(c["slots"]["Unit"], c["cons"])
        c["T"] = sorted(set(toks), key=ukey)
        c["main"] = toks[0] if toks else None
        files = paths_in(c["slots"]["Site"]) | heading_paths(c["section"])
        c["files"] = sorted(files)
        c["doc"] = bool(files) and all(p.endswith(".md") for p in files)
        c["new"] = bool(re.search(r"\(new\b|\bnew\)", c["section"] or "")) or c["slots"]["Site"].strip().lower().startswith("new")
        for a in EXTRA_FROM.get(k, ()):
            if a not in c["live"]:
                c["live"].append(a)
                c["cons"].append((a, True, "AC3_R placement"))
    for k, v in SYNTH.items():
        slots = collections.defaultdict(str)
        slots["Depends"] = ", ".join(v["depends"])
        ch[k] = {"title": v["title"], "file": v["file"], "line": 0, "section": None, "slots": slots, "slot_line": {},
                 "cons": [(a, True, "") for a in v["live"]], "live": list(v["live"]), "T": v["T"], "main": v["T"][0],
                 "files": v["files"], "doc": False, "new": True, "synthetic": True,
                 "after_holders_of": v.get("after_holders_of", []), "last_in_unit_for_files": v.get("last_in_unit_for_files", False)}
    return acts, canon, S, D, ch, act_files, unknown


def landings(ch, D, ov=None):
    """L[(M, a)] = unit the part of live constituent a lands in, per the rules in WORK_ORDER.md section 2."""
    L, why = {}, {}
    for k, c in ch.items():
        T = c["T"]
        for a in c["live"]:
            u = norm_unit(action_unit(a))
            if not T:
                L[(k, a)], why[(k, a)] = u, "own unit (no Unit slot)"
            elif k in OWNUNIT:
                L[(k, a)], why[(k, a)] = u, "own unit (the Unit slot lands each row with its action)"
            elif u in T or (u == "U0R" and "U0" in T):
                L[(k, a)], why[(k, a)] = u, "own unit, named in the Unit slot"
            elif all(ukey(t) < ukey(u) for t in T):
                L[(k, a)], why[(k, a)] = u, "own unit (the Unit slot writes it early in end form; confirmed in place here)"
            elif c["doc"] or c["new"]:
                t = min((t for t in T if ukey(t) > ukey(u)), key=ukey)
                L[(k, a)], why[(k, a)] = t, ("deferred to the next Unit-slot unit (doc site)" if c["doc"] else
                                             "deferred to the next Unit-slot unit (site born there)")
            else:
                L[(k, a)], why[(k, a)] = u, "own unit (implicit step: code/test site, blast closed in its unit)"
            if a in PULLS and not (PULLS[a][2:] == ("code",) and c["doc"]):
                L[(k, a)], why[(k, a)] = PULLS[a][0], "pulled: " + PULLS[a][1]
            if (k, a) in RELOC:
                L[(k, a)], why[(k, a)] = RELOC[(k, a)][0], RELOC[(k, a)][1]
    # in-change dependencies: a part never lands before the in-change constituent it needs
    changed = True
    while changed:
        changed = False
        for k, c in ch.items():
            live = set(c["live"])
            for a in c["live"]:
                for b, cls in D.get(a, ()):
                    cls = (ov or {}).get((a, b), cls)
                    if b not in live or cls not in ("order", "rev", "inchange", "doconly"):
                        continue
                    if cls == "doconly" and not c["doc"]:
                        continue
                    x, y = (a, b) if cls != "rev" else (b, a)  # x needs y
                    if ukey(L[(k, y)]) > ukey(L[(k, x)]):
                        L[(k, x)] = L[(k, y)]
                        why[(k, x)] = f"deferred to land with {y} in this change"
                        changed = True
    return L, why


def holders(ch, L):
    h = collections.defaultdict(list)
    for (k, a), u in L.items():
        h[a].append((k, u))
    return h


def own_holders(a, H, ch, act_files):
    """Holders whose Site names one of the action's own site files; all holders when none does."""
    af = act_files.get(a, set())
    own = [(k, u) for k, u in H.get(a, ()) if af & {fkey(p) for p in ch[k]["files"]}]
    return own or list(H.get(a, ()))


def steps_of(ch, L):
    st = collections.defaultdict(set)
    for (k, a), u in L.items():
        st[k].add(u)
    for k, c in ch.items():
        st[k] |= {t for t in c["T"] if not (t == "U0" and "U0R" in st[k] and "U0" not in st[k])}
    return {k: sorted(v, key=ukey) for k, v in st.items()}


def edges(ch, D, L, act_files, canon, overrides=None):
    """[(src_step, dst_step, kind, note)], a step being (M-ID, unit). kind: action | dep-A | dep-M."""
    overrides = overrides or {}
    H = holders(ch, L)
    ST = steps_of(ch, L)
    E = []
    for a, deps in D.items():
        if a not in H:
            continue
        for b, cls in deps:
            cls = overrides.get((a, b), cls)
            if cls not in ("order", "rev", "doconly") or b not in H:
                continue
            x, y = (a, b) if cls != "rev" else (b, a)  # x needs y
            for kx, ux in own_holders(x, H, ch, act_files):
                if cls == "doconly" and not ch[kx]["doc"]:
                    continue
                cand = [(ky, uy) for ky, uy in own_holders(y, H, ch, act_files)
                        if ky != kx and not (ch[ky]["doc"] and not ch[kx]["doc"])]  # code never waits on a doc edit
                if cand:
                    first = min((t[1] for t in cand), key=ukey)  # y's own change: its first landing, every part of it
                    for ky, uy in cand:
                        if uy == first:
                            E.append(((ky, uy), (kx, ux), "action", f"{x} needs {y} ({cls})"))
    for a in H:  # a blast edit follows its cause
        own = own_holders(a, H, ch, act_files)
        ownk = {k for k, _ in own}
        for k, u in H[a]:
            if k in ownk:
                continue
            cand = [(ko, uo) for ko, uo in own if not (ch[ko]["doc"] and not ch[k]["doc"])]
            if cand:
                ko, uo = min(cand, key=lambda t: ukey(t[1]))
                E.append(((ko, uo), (k, u), "blast", f"{k} carries {a}'s blast"))
    for k, c in ch.items():
        mine = ST[k]
        if not mine:
            continue
        dep = c["slots"]["Depends"]
        for b, s, e in expand_a(dep, canon):
            if b not in H or b in c["live"] or dep[e:e + 10].startswith(" [follows]"):
                continue
            cand = [(kb, ub) for kb, ub in own_holders(b, H, ch, act_files)
                    if kb != k and not (ch[kb]["doc"] and not c["doc"])]
            if cand:
                first = min((t[1] for t in cand), key=ukey)
                tgt = next((u for u in mine if ukey(u) >= ukey(first)), mine[-1])
                for kb, ub in cand:
                    if ub == first:
                        E.append(((kb, ub), (k, tgt), "dep-A", f"{k} Depends {b}"))
        for n, s, e in expand_m(dep):
            if n == k or n not in ch or not ST.get(n) or dep[e:e + 10].startswith(" [follows]"):
                continue
            theirs = ST[n]
            for u in mine:
                if u in theirs:
                    E.append(((n, u), (k, u), "dep-M", f"{k} Depends {n} (same unit)"))
            # the dependent completes no earlier than what it depends on starts; its first step at/after that
            tgt = next((u for u in mine if ukey(u) >= ukey(theirs[0])), mine[-1])
            E.append(((n, theirs[0]), (k, tgt), "dep-M", f"{k} Depends {n}"))
    return E, ST


def settle(ch, D, L, why, act_files, overrides=None):
    """Earliest consistent landings: defer a part until every part it needs has landed (order deps, blasts).

    Returns the moves {(M, a): (old unit, new unit, reason)}; L and why are updated in place.
    """
    overrides = overrides or {}
    moves = {}
    for _ in range(200):
        H = holders(ch, L)
        changed = False
        for a, deps in D.items():
            if a not in H:
                continue
            for b, cls in deps:
                cls = overrides.get((a, b), cls)
                if cls not in ("order", "rev", "doconly") or b not in H:
                    continue
                x, y = (a, b) if cls != "rev" else (b, a)
                ys = [(k, u) for k, u in own_holders(y, H, ch, act_files)]
                for kx, ux in own_holders(x, H, ch, act_files):
                    if cls == "doconly" and not ch[kx]["doc"]:
                        continue
                    need = [u for k, u in ys if k != kx and not (ch[k]["doc"] and not ch[kx]["doc"])]
                    if need:
                        top = min(need, key=ukey)  # x needs y's own change, i.e. its first landing
                        if ukey(top) > ukey(L[(kx, x)]):
                            old = moves.get((kx, x), (L[(kx, x)],))[0]
                            L[(kx, x)] = top
                            why[(kx, x)] = f"deferred: {x} needs {y}, which lands in {top}"
                            moves[(kx, x)] = (old, top, why[(kx, x)])
                            changed = True
        H = holders(ch, L)
        for a in H:
            own = own_holders(a, H, ch, act_files)
            ownk = {k for k, _ in own}
            for k, u in H[a]:
                if k in ownk:
                    continue
                need = [uo for ko, uo in own if not (ch[ko]["doc"] and not ch[k]["doc"])]
                if need:
                    top = min(need, key=ukey)  # a blast follows the first landing of its cause
                    if ukey(top) > ukey(L[(k, a)]):
                        old = moves.get((k, a), (L[(k, a)],))[0]
                        L[(k, a)] = top
                        why[(k, a)] = f"deferred: blast of {a}, whose own change lands in {top}"
                        moves[(k, a)] = (old, top, why[(k, a)])
                        changed = True
        if not changed:
            break
    return moves


# ---- A-C2 rulings on action-level dependencies (each read in its action's Depends text) -------------
# "ign": no ordering (a co-landing / same-site note the merges carry, a split of ownership, or a duplicate);
# "order": the first action needs the second; "inchange": order inside a change that carries both only.
DEP_RULINGS = {
    ("A.U11.S03", "A.U16.16"): ("ign", "A.U16.16 edits nearby FRAM driver comments only"),
    ("A.U0.38", "A.U4.07"): ("ign", "the V31 parts are carried by A.U4.07, not written by A.U0.38"),
    ("A.U0.38", "A.U7.25"): ("ign", "the V03/V33 parts are carried by A.U7.25, not written by A.U0.38"),
    ("A.U0.58", "A.U5.17"): ("ign", "same BACKLOG item, merged (M.DOCS)"),
    ("A.U11.09", "A.U12.14"): ("ign", "the VOC half is A.U12.14's own file"),
    ("A.U36.546", "A.U37.06"): ("ign", "same BACKLOG paragraphs; A.U37.06 edits after it"),
    ("A.U36.548", "A.U37.06"): ("ign", "same BACKLOG paragraphs; A.U37.06 edits after it"),
    ("A.U36.548", "A.U37.15"): ("ign", "A.U37.15 deletes the plan pointers in phase D, after it"),
    ("A.U10.13", "A.U11.39"): ("ign", "A.U11.39 is this action (A-C keeps A.U10.13)"),
    ("A.S0930.34", "A.U26.71"): ("order", "the guard derivation it checks is A.U26.71's"),
    ("A.S0930.34", "A.U25.36"): ("order", "the twin-run check it extends is A.U25.36's"),
    ("A.U10.09", "A.U11.03"): ("order", "the A.2 text follows A.U11.03's escalation"),
    ("A.U10.15", "A.U11.03"): ("ign", "A.U10.15 keeps the unpause half only; the reset half is A.U11.03's own"),
    ("A.U10.15", "A.U11.04"): ("ign", "A.U10.15 keeps the unpause half only; the reset half is A.U11.04's own"),
    ("A.S0930.14", "A.U16.R03"): ("order", "S4 cancels the FRAM manager's supervised task"),
    ("A.S0930.19", "A.U26.06"): ("order", "the guard sees device scripts from A.U26.06"),
    ("A.S0930.19", "A.U26.74"): ("order", "flag names from A.U26.74"),
    ("A.S0930.17", "A.U24.42"): ("inchange", "only its allocation-budget test part needs A.U24.42's file"),
    ("A.U28.37", "A.U28.12"): ("ign", "A.U28.12 is a SPEC pointer to the same B.10 text, not a prerequisite"),
    ("A.U28.38", "A.U28.12"): ("ign", "A.U28.12 is a SPEC pointer; the BACKLOG list records the unit's tooling changes"),
    ("A.U18.03", "A.U14.30"): ("ign", "a settled-by reference (OR112.a), not an ordering"),
    ("A.U18.18", "A.U14.30"): ("ign", "a settled-by reference (OR112.a); A.U14.30's text cites these bounds"),
    ("A.U14.30", "A.U19.24"): ("doconly", "only the SPEC text points at the webserver's EAGAIN side"),
}
for _m in ("A.U10.01", "A.U10.02", "A.U10.03", "A.U10.04", "A.U10.05", "A.U11.01", "A.U15.03", "A.U15.31", "A.U17.14",
           "A.U17.28", "A.U17.29", "A.U12.13", "A.U24.39", "A.U25.14", "A.U25.23", "A.U23.29", "A.U3.02", "A.U35.04"):
    DEP_RULINGS[("A.U35.35", _m)] = ("inchange", "A.U35.35's checklist covers every counter at U35; its K.28 gap fill "
                                     "lands with its own counter's unit (AC3_R R-08 (e)) and needs no other row")
for _m in ("A.U10.R01", "A.U13.R01", "A.U15.R01", "A.U15.R02", "A.U15.R03", "A.U15.R04", "A.U16.R01", "A.U16.R02",
           "A.U16.R03", "A.U18.R01"):
    DEP_RULINGS[("A.U14.R01", _m)] = ("doconly", "F.2 and CLAUDE.md describe the mechanism once it exists")
# Parts that land outside their ID's unit by an action's own text.
PULLS = {
    "A.U28.13": ("U0R", "A.SDEP.05: \"A.U28.13 (pulled forward)\" into the GitHub Actions pin refresh", "code"),
    "A.U37.15": ("D", "its own title: \"Phase D: delete the plan and audit/\"; needs A.C.11", "all"),
    "A.U14.17": ("U13", "A.U14.17 (a)'s code half lands with A.U13.R01 in U13 (M.SRC_SENS.008/.009: the boot clear "
                 "is called from I2C.__init__ there, so every fake and the generated call move with it)", "code"),
}
# A-C3 placements folded in before the lead applies the body text (AC3_R.md R-01, R-02, R-04, R-08 (h);
# AC3_S.md S-01..S-17 and its section 4). Proposed new changes carry the IDs AC3_S proposes (the lead may renumber).
EXTRA_FROM = {
    "M.PROC.022": ["A.U35.03", "A.U35.04", "A.U35.05", "A.U35.08", "A.U35.09", "A.U35.15", "A.U35.22", "A.U35.23",
                   "A.U35.28", "A.U35.35", "A.U35.37", "A.U35.41", "A.U35.50", "A.U35.51"],
    "M.PROC.021": ["A.U32.05"],
    "M.PROC.003": ["A.U0.38"],
    "M.SRC_SENS.030": ["A.U10.31"], "M.SRC_NET.211": ["A.U10.31"], "M.SRC_CORE.060": ["A.U10.31"],
    "M.TEST_UNIT.338": ["A.U24.38"], "M.TWIN.040": ["A.U25.63"], "M.HW_DEV.051": ["A.U26.47"],
    "M.HW_DEV.045": ["A.U26.47"], "M.GEN.009": ["A.U6.20"], "M.WEB.074": ["A.U8.15"], "M.TSC.165": ["A.S0930.34"],
    "M.PROC.018": ["A.U28.35"], "M.DOCS.064": ["A.C.10"], "M.SRC_SENS.054": ["A.U0.35"],
    "M.SRC_SENS.033": ["A.U10.21", "A.U11.31"], "M.SRC_SENS.061": ["A.U10.31"], "M.HW_BENCH.050": ["A.U2.03"],
    "M.TEST_HELP.001": ["A.U21.13"], "M.WEB.054": ["A.U23.36"], "M.WEB.031": ["A.U23.04"], "M.PROC.023": ["A.U35.22"],
}
_S05 = {"M.GEN.065": "buildgen/", "M.SCR.075": "scripts/", "M.TSC.228": "tests_scripts/", "M.TEST_HELP.068": "tests/",
        "M.TEST_UNIT.340": "tests/", "M.TWIN.165": "digital_twin/", "M.HW_BENCH.136": "tests_hardware/",
        "M.HW_DEV.158": "tests_hardware/device_scripts/"}
SYNTH = {
    "M.GEN.064": {"title": "Re-vendor freezefs at upstream main, unmodified (AC3_S S-01)", "file": "audit/consolidation/M_GEN.md",
                  "live": ["A.SDEP.07"], "T": ["U0"], "files": ["ext/freezefs/"], "depends": ["A.SDEP.01", "A.SDEP.02"]},
    "M.SRC_CORE.132": {"title": "D.15 member order in the remaining classes (AC3_S S-04)", "file": "audit/consolidation/M_SRC_CORE.md",
                       "live": ["A.U10.33"], "T": ["U10"], "files": ["src/config_manager.py", "src/print_log.py", "src/asy_fram_driver.py"],
                       "depends": [], "last_in_unit_for_files": True},
    "M.SRC_SENS.093": {"title": "D.15 member order in the remaining classes (AC3_S S-04)", "file": "audit/consolidation/M_SRC_SENS.md",
                       "live": ["A.U10.33"], "T": ["U10"], "files": ["src/asy_bmp3xx_driver.py", "src/asy_neopixel_driver.py",
                       "src/asy_notification_service.py", "src/asy_scd30_driver.py", "src/asy_sgp40_driver.py", "src/asy_spi_driver.py"],
                       "depends": [], "last_in_unit_for_files": True},
    "M.HW_BENCH.137": {"title": "B2 host annotations across the cluster (AC3_S S-06)", "file": "audit/consolidation/M_HW_BENCH.md",
                       "live": ["A.U20.33"], "T": ["U20"], "files": ["tests_hardware/"], "depends": []},
    "M.TEST_UNIT.341": {"title": "File-local builders take the private form (AC3_S S-07)", "file": "audit/consolidation/M_TEST_UNIT.md",
                        "live": ["A.U24.76"], "T": ["U24"], "files": ["tests/"], "depends": ["A.U24.49"]},
    "M.TWIN.166": {"title": "File-local builders take the private form (AC3_S S-07)", "file": "audit/consolidation/M_TWIN.md",
                   "live": ["A.U24.76"], "T": ["U24"], "files": ["tests/test_digital_twin_isl29125.py"], "depends": ["A.U24.49"]},
    "M.DOCS.109": {"title": "The integrate-module skill points into Part K (AC3_S S-13 = AC3_R R-04)", "file": "audit/consolidation/M_DOCS.md",
                   "live": ["A.U36.543"], "T": ["U36"], "files": [".claude/skills/integrate-module/SKILL.md"],
                   "depends": ["M.SPEC.142", "M.SPEC.046"]},
    "M.PROC.R04": {"title": "U36: two baseline runs of the Part K skill (AC3_R R-04; ID pending)", "file": "audit/consolidation/M_PROC.md",
                   "live": ["A.U36.543"], "T": ["U36"], "files": [], "depends": ["M.DOCS.109"]},
    "M.PROC.046": {"title": "U10 rename and key sweeps run once over the whole tree (AC3_S S-15)", "file": "audit/consolidation/M_PROC.md",
                   "live": ["A.U10.18", "A.U10.35", "A.U10.37", "A.U10.38", "A.U10.40", "A.U10.43", "A.U10.44"], "T": ["U10"],
                   "files": [], "depends": [], "after_holders_of": ["A.U10.18", "A.U10.35", "A.U10.37", "A.U10.38", "A.U10.40",
                                                                   "A.U10.43", "A.U10.44"]},
    "M.PROC.047": {"title": "U36 host-scope reorder runs once over every Python scope (AC3_S S-15)", "file": "audit/consolidation/M_PROC.md",
                   "live": ["A.U36.038"], "T": ["U36"], "files": [], "depends": ["M.TSC.044", "M.TSC.064"],
                   "after_holders_of": ["A.U36.038"]},
}
for _k, _d in _S05.items():
    SYNTH[_k] = {"title": "Docstrings become comments in this cluster's scope (AC3_S S-05)",
                 "file": f"audit/consolidation/M_{_k.split('.')[1]}.md", "live": ["A.U10.34"], "T": ["U10"],
                 "files": [_d], "depends": []}
# The B0 baseline actions (record, toolchain and corpus, non-interference rules, measurement).
BASELINE = ["A.U0.02", "A.U0.03", "A.U0.04", "A.U0.06"]
# Change-level cycles settled at step level as one co-landing commit (M-file ledger notes record each).
COLAND = [("M.TWIN.019", "M.TWIN.033"), ("M.DOCS.008", "M.DOCS.011")]
# Changes that create nothing (their Unit slot reads "none", A-C2): no step.
NOSTEP = {"M.TSC.183", "M.TSC.225"}
# Changes whose Unit slot lands every row with its own action ("per row as listed", "each adding action's own unit").
OWNUNIT = {"M.DOCS.024", "M.DOCS.064", "M.DOCS.066", "M.SPEC.156"}
# Per-change relocations a Unit slot states in words (the parser cannot read them from the unit tokens).
RELOC = {
    ("M.SRC_SENS.008", "A.U14.17"): ("U13", "Unit slot: A.U14.17 (a)'s code half co-lands with A.U13.R01 in U13"),
    ("M.GEN.005", "A.U11.10"): ("U20", "Unit slot: batch removal co-lands with A.U11.10 in U20's commit"),
    ("M.SPEC.020", "A.U11.10"): ("U20", "Unit slot: A.U11.10/.11 co-land in one commit with U20's codegen action"),
    ("M.SPEC.020", "A.U11.11"): ("U20", "Unit slot: A.U11.10/.11 co-land in one commit with U20's codegen action"),
    ("M.SRC_CORE.012", "A.U10.15"): ("U11", "Unit slot: A.U10.15 co-lands with A.U11.03/A.U11.04"),
    ("M.SRC_CORE.044", "A.U35.43"): ("U11", "Unit slot: A.U35.43 pulled into U11 (needs A.U11.28's deferral)"),
    ("M.SRC_CORE.065", "A.U10.11"): ("U16", "Unit slot: the _read() half is pulled into U16's rewrite"),
    ("M.SRC_CORE.065", "A.U11.16"): ("U16", "Unit slot: the _read() half is pulled into U16's rewrite"),
    ("M.SRC_SENS.017", "A.U11.09"): ("U12", "Unit slot: lands with A.U12.14 in U12"),
    ("M.SRC_SENS.017", "A.U0.41"): ("U12", "Unit slot: the comment lands with A.U12.14 in U12"),
    ("M.SRC_SENS.032", "A.U36.544"): ("U10", "Unit slot: the pointer lands with U10 (its target exists at HEAD)"),
    ("M.TOOL.037", "A.U36.544"): ("U21", "Unit slot: the pointer edits land with U21's rewrite of the same lines"),
    ("M.TSC.087", "A.U24.55"): ("U25", "Unit slot: lands with A.U24.55's file edits in U25"),
    ("M.TWIN.031", "A.S0930.24"): ("U25", "Unit slot: feed_times co-lands in U25 (AC_NOTES 36)"),
    ("M.TWIN.152", "A.S0930.36"): ("U25", "Unit slot: the L2 half co-lands in U25"),
    ("M.TEST_HELP.011", "A.S0930.24"): ("U11", "Unit slot: feed_times lands inside stage 1 (U11)"),
    ("M.SCR.061", "A.S0930.04"): ("U27", "AC3_R R-08 (h): A.S0930.04's CRC16 rerun runs on U27's runner"),
    ("M.TEST_UNIT.211", "A.U1.26"): ("U18", "AC3_R R-08 (a): the comment lands with this change in U18 (a label fix; no U1 check reads it)"),
    ("M.TEST_UNIT.236", "A.U24.74"): ("U12", "Unit slot \"stage U12 with the race fix\": the R.26 regression test bites with the fix (OR109.a (0); AC3_R R-08 (d))"),
    ("M.TEST_HELP.033", "A.U24.34"): ("U25", "From: content travelling host-side with the file's U25 move (AC3_R R-08 (c))"),
    ("M.TEST_HELP.033", "A.U24.36"): ("U25", "From: content travelling host-side with the file's U25 move (AC3_R R-08 (c))"),
    ("M.SRC_CORE.063", "A.U35.35"): ("U11", "the K.28 gap fill lands with the counter's owning unit (AC3_R R-08 (e))"),
    ("M.TEST_HELP.033", "A.U24.37"): ("U25", "From: content travelling host-side with the file's U25 move (AC3_R R-08 (c))"),
}


def hw_inventory(canon):
    """{action: set(rounds)} from C.md's hardware-duty inventory; 'every' rows are the frame, not a unit's need."""
    out = collections.defaultdict(set)
    rows = []
    for ln in open("audit/actions/C.md"):
        m = re.match(r"^\| (H\d\d) \| (.*)$", ln)
        if not m:
            continue
        cols = [c.strip() for c in ln.strip().strip("|").split("|")]
        hid, duty, src, level, rnd = cols[0], cols[1], cols[2], cols[3], cols[4]
        rounds = sorted(set(re.findall(r"R\d", rnd)))
        rows.append((hid, duty, rnd, rounds))
        if not rounds:
            continue
        for a, _, _ in expand_a(duty + " " + src, canon):
            for r in rounds:
                out[a].add((r, hid))
    return out, rows


def rulings(D):
    ov = {}
    for a, l in D.items():
        for b, cls in l:
            if cls == "co":
                ov[(a, b)] = "ign"
    for k, (cls, _) in DEP_RULINGS.items():
        ov[k] = cls
    return ov


# ---- in-unit order -------------------------------------------------------------------------------------
def scc_order(nodes, edges):
    """Tarjan SCCs, returned in a topological order (each SCC a list), dependencies first."""
    adj = collections.defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
    idx, low, on, st, out = {}, {}, set(), [], []
    counter = [0]
    sys.setrecursionlimit(100000)

    def strong(v):
        idx[v] = low[v] = counter[0]
        counter[0] += 1
        st.append(v)
        on.add(v)
        for w in sorted(adj[v]):
            if w not in idx:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            out.append(sorted(comp))
    for v in sorted(nodes):
        if v not in idx:
            strong(v)
    out.reverse()  # Tarjan emits sinks first
    return out


# ---- test references ------------------------------------------------------------------------------------
TEST_GLOBS = ["tests/test_*.py", "tests_scripts/test_*.py", "tests_js/*.test.js"]
IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
PATHREF_RE = re.compile(r"((?:src|buildgen|scripts|toolchain|digital_twin|js|html|devices|tests_hardware|tests|\.github)/[\w./-]+|"
                        r"[\w.-]+\.(?:md|toml|ini|json|sh|yml))")


def test_index():
    idx = {}
    for g in TEST_GLOBS:
        for f in sorted(glob.glob(g)):
            t = open(f, encoding="utf-8", errors="replace").read()
            names = set()
            for m in IMPORT_RE.finditer(t):
                n = (m.group(1) or m.group(2)).split(".")[0]
                names.add(re.sub(r"^asy_", "", n))
            for m in re.finditer(r"""from\\s+['"]([^'"]+)['"]|import\\(['"]([^'"]+)['"]\\)""", t):
                p = (m.group(1) or m.group(2))
                names.add(re.sub(r"^asy_", "", p.rsplit("/", 1)[-1].rsplit(".", 1)[0]))
            for m in PATHREF_RE.finditer(t):
                p = m.group(1)
                names.add(re.sub(r"^asy_", "", p.rsplit("/", 1)[-1].rsplit(".", 1)[0]))
                names.add(p)
            idx[f] = names
    return idx


def scoped_tests(files, tidx):
    out = set()
    for p in files:
        p = p.rstrip("/")
        if re.match(r"(tests/test_|tests_scripts/test_|tests_js/.*\\.test\\.js)", p) and not p.endswith("/"):
            out.add(p)
            continue
        stem = re.sub(r"^asy_", "", p.rsplit("/", 1)[-1].rsplit(".", 1)[0])
        if not stem or len(stem) < 3:
            continue
        host_only = p.endswith((".md", ".sh", ".yml", ".ini", ".lock")) or p.startswith(
            ("scripts/", "toolchain/", ".github/", "audit/", "pyproject", "package", "tsconfig", "eslint", "vitest"))
        for f, names in tidx.items():
            if host_only and not f.startswith("tests_scripts/"):
                continue
            if stem in names or p in names:
                out.add(f)
        if p.startswith("buildgen/"):
            out |= {f for f in tidx if re.match(r"tests/test_sensortask_\w+\.py$", f)}
        m = re.match(r"devices/(\w+)\.toml$", p)
        if m:
            out |= {f for f in tidx if f in (f"tests/test_sensortask_{m.group(1)}.py",)}
    return out


# ---- the work order -------------------------------------------------------------------------------------
GATE = [
    "scripts/lint.sh (ruff, shellcheck, actionlint, zizmor)",
    "scripts/typecheck.sh (the three mypy passes)",
    "scripts/test.sh (unit tier at gc -1, with its backgrounded tests_scripts pytest tier)",
    "GC_THRESHOLD=32768 scripts/test.sh (unit tier at the boot threshold)",
    "scripts/run_digital_twin_ci.sh <device> for every devices/*.toml (twin tier, both GC stages)",
    "npm run lint, lint:html, lint:css, typecheck; npm run test:unit; npm run test:put-matrix (web tier, port-binding)",
]
COVERAGE = "scripts/test.sh --coverage and npm run test:coverage (the unit touches src/; the report never gates, the test result does)"


def run():
    acts, canon, S, D, ch, AF, unknown = build()
    OV = rulings(D)
    L, why = landings(ch, D, OV)
    L0 = dict(L)
    moves = settle(ch, D, L, why, AF, OV)
    E, ST = edges(ch, D, L, AF, canon, OV)
    H = holders(ch, L)
    for k, c in ch.items():  # sweeps run after the per-file changes they complete
        for a in c.get("after_holders_of", ()):
            for kh, u in H.get(a, ()):
                if kh != k and u in ST[k]:
                    E.append(((kh, u), (k, u), "sweep", f"{k} sweeps {a} after {kh}"))
        if c.get("last_in_unit_for_files"):
            mine = {fkey(p) for p in c["files"]}
            u = c["T"][0]
            for k2, c2 in ch.items():
                if k2 != k and u in ST.get(k2, ()) and mine & {fkey(p) for p in c2["files"]}:
                    E.append(((k2, u), (k, u), "sweep", f"{k} reorders after {k2}"))
    viol = [e for e in E if ukey(e[0][1]) > ukey(e[1][1])]
    return dict(acts=acts, canon=canon, S=S, D=D, ch=ch, AF=AF, OV=OV, L=L, L0=L0, why=why, moves=moves, E=E,
                ST=ST, H=H, viol=viol, unknown=unknown)


def main(write=False):
    R = run()
    ch, L, why, E, ST, H = R["ch"], R["L"], R["why"], R["E"], R["ST"], R["H"]
    # deduplicated step edges
    ded = collections.defaultdict(set)
    for s_, d_, kind, note in E:
        if s_ != d_:
            ded[(s_, d_)].add(kind)
    steps = sorted({(k, u) for k, us in ST.items() for u in us}, key=lambda t: (ukey(t[1]), t[0]))
    carried = collections.defaultdict(list)
    for (k, a), u in L.items():
        carried[(k, u)].append(a)
    # in-unit order: action-level and sweep edges first (their cycles co-land as one commit), then Depends and
    # blast edges in that priority, each added only where it closes no cycle (a dropped edge is recorded)
    PRI = [("action", "sweep"), ("dep-A",), ("blast",), ("dep-M",)]
    order, cycles, dropped = {}, [], collections.Counter()
    for u in UNITS:
        nodes = [k for k, uu in steps if uu == u]
        if not nodes:
            continue
        ue = [(s_[0], d_[0], kinds) for (s_, d_), kinds in ded.items() if s_[1] == u and d_[1] == u and s_[0] != d_[0]]
        base = [(a, b) for a, b, kinds in ue if kinds & set(PRI[0])]
        for a, b in COLAND:  # settled change-level cycles: one commit
            if a in nodes and b in nodes:
                base += [(a, b), (b, a)]
        comps = scc_order(nodes, base)
        gid = {n: i for i, c in enumerate(comps) for n in c}
        cycles += [{"unit": u, "steps": c} for c in comps if len(c) > 1]
        gadj = collections.defaultdict(set)
        for a, b in base:
            if gid[a] != gid[b]:
                gadj[gid[a]].add(gid[b])

        def reaches(x, y):
            seen, st = {x}, [x]
            while st:
                z = st.pop()
                if z == y:
                    return True
                for w in gadj[z]:
                    if w not in seen:
                        seen.add(w)
                        st.append(w)
            return False
        for level in PRI[1:]:
            for a, b, kinds in sorted(ue):
                if not (kinds & set(level)) or kinds & set(PRI[0]):
                    continue
                ga, gb = gid[a], gid[b]
                if ga == gb or gb in gadj[ga]:
                    continue
                if reaches(gb, ga):
                    dropped[level[0]] += 1
                    continue
                gadj[ga].add(gb)
        # topological order of the groups (Kahn, stable by first member)
        indeg = collections.Counter()
        for x in list(gadj):
            for y in gadj[x]:
                indeg[y] += 1
        ready = sorted((g for g in range(len(comps)) if indeg[g] == 0), key=lambda g: comps[g][0])
        seq = []
        while ready:
            g = ready.pop(0)
            seq.append(comps[g])
            for y in sorted(gadj[g]):
                indeg[y] -= 1
                if indeg[y] == 0:
                    ready.append(y)
            ready.sort(key=lambda g: comps[g][0])
        order[u] = seq
    # unit reachability and shared files
    uadj = collections.defaultdict(set)
    for (s_, d_) in ded:
        if s_[1] != d_[1]:
            uadj[s_[1]].add(d_[1])
    reach = {}
    for u in UNITS:
        seen, st = set(), [u]
        while st:
            x = st.pop()
            for y in uadj[x]:
                if y not in seen:
                    seen.add(y)
                    st.append(y)
        reach[u] = seen
    ufiles = collections.defaultdict(set)
    for k, u in steps:
        ufiles[u] |= {p.rstrip("/") for p in ch[k]["files"]}

    def overlap(a, b):
        for p in a:
            for q in b:
                if p == q or p.startswith(q + "/") or q.startswith(p + "/") or fkey(p) == fkey(q):
                    return True
        return False
    def named(k, u):
        return u in ch[k]["T"] or (u == "U0R" and "U0" in ch[k]["T"])
    tidx = test_index()
    hw, hwrows = hw_inventory(R["canon"])
    units = []
    for i, u in enumerate(UNITS):
        us = [k for k, uu in steps if uu == u]
        if not us:
            continue
        acts_here = sorted({a for k in us for a in carried[(k, u)]})
        files = ufiles[u]
        blast = set()
        for k in us:
            blast |= paths_in(ch[k]["slots"].get("Blast carried by", ""))
        scoped = sorted(scoped_tests(files | blast, tidx))
        indep = [v for v in UNITS[i + 1:] if any(uu == v for _, uu in steps)
                 and v not in uadj[u] and not overlap(files, ufiles[v])]
        rounds = collections.defaultdict(set)
        for a in acts_here:
            for r, h in hw.get(a, ()):
                rounds[r].add(h)
        touches_src = any(p.startswith("src/") for p in files)
        units.append({
            "unit": u, "steps": len(us), "actions": len(acts_here),
            "explicit_steps": sum(1 for k in us if named(k, u)),
            "implicit_steps": sum(1 for k in us if not named(k, u)),
            "order": order[u],
            "files": sorted(files), "scoped_tests": scoped,
            "full_gate": GATE + ([COVERAGE] if touches_src else []),
            "independent_later_units": indep,
            "hardware_rounds": {r: sorted(v) for r, v in sorted(rounds.items())},
        })
    fwd = collections.Counter()
    fwd_pairs = set()
    for a, l in R["D"].items():
        for b, cls in l:
            x, y = (a, b) if cls != "rev" else (b, a)
            if ukey(action_unit(y)) > ukey(action_unit(x)):
                fwd_pairs.add((a, b))
                fwd[R["OV"].get((a, b), cls)] += 1
    checks = {
        "action_depends_refs": sum(len(l) for l in R["D"].values()),
        "action_depends_to_a_later_unit": {"pairs": len(fwd_pairs), "after_reading": dict(fwd)},
        "changes": len(ch), "steps": len(steps), "edges": len(ded),
        "edge_kinds": dict(collections.Counter(k for v in ded.values() for k in v)),
        "violations_remaining": [[list(e[0]), list(e[1]), e[2], e[3]] for e in R["viol"]],
        "deferrals": len(R["moves"]), "in_unit_cycles": cycles, "in_unit_edges_dropped_to_break_cycles": dict(dropped),
        "no_step_changes": sorted(k for k in ch if not ST.get(k)),
        "unknown_action_refs": sorted(set(R["unknown"])),
    }
    wo = {
        "generated": "2026-10-01", "units_sequence": UNITS, "checks": checks, "units": units,
        "steps": [{"change": k, "unit": u, "file": ch[k]["file"], "title": ch[k]["title"],
                   "carries": sorted(carried[(k, u)]),
                   "landing": {a: why[(k, a)] for a in sorted(carried[(k, u)])},
                   "named_in_unit_slot": named(k, u)} for k, u in steps],
        "rulings": {f"{a}|{b}": v for (a, b), v in DEP_RULINGS.items()},
        "pulls": PULLS, "relocations": {f"{k}|{a}": v for (k, a), v in RELOC.items()},
        "deferrals": [{"change": k, "action": a, "from": o, "to": n, "reason": r}
                      for (k, a), (o, n, r) in sorted(R["moves"].items())],
        "hardware_inventory_rows": [{"id": h, "duty": d, "round": r} for h, d, r, _ in hwrows],
    }
    print({k: (len(v) if isinstance(v, list) else v) for k, v in checks.items() if k != "edge_kinds"}, checks["edge_kinds"])
    if write:
        json.dump(wo, open(f"{OUT}/work_order.json", "w"), indent=1)
        json.dump({"units": {k: ST[k] for k in sorted(ST)},
                   "edges": [[s_[0], s_[1], d_[0], d_[1], sorted(v)] for (s_, d_), v in sorted(ded.items())]},
                  open(f"{OUT}/graph.json", "w"))
        json.dump(checks, open(f"{OUT}/check.json", "w"), indent=1)
    return wo, R




def m_file_notes():
    rows = []
    for f in sorted(glob.glob(f"{ROOT}/M_*.md")):
        t = open(f).read()
        if "## A-C2 order notes" not in t:
            continue
        for ln in t[t.index("## A-C2 order notes"):].splitlines():
            m = re.match(r"^\| (M\.[A-Z_]+\.\d+) \| (Unit|Depends) \| (.*) \| (.*) \|$", ln)
            if m:
                rows.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return rows


ROUND_NAMES = {"R0": "bench host, no board", "R1": "first contact and the default run", "R2": "operator round (owner at the bench)",
               "R3": "gated wear run", "R4": "reflash rows (`flash_cycle`)", "R5": "soak durations",
               "R6": "12.4-day rollover", "R7": "release proof"}


def render_md(wo, R):
    ch, ST = R["ch"], R["ST"]
    c = wo["checks"]
    units = wo["units"]
    notes = m_file_notes()
    L = []
    w = L.append
    w("# A-C2 work order (2026-10-01)")
    w("")
    w("The order in which B1-B5 and phase C apply the merged changes of `audit/consolidation/M_*.md`, step by step, with "
      "each unit's test schedule (LEAD/R34). Machine-readable twin: `audit/order/work_order.json` (every step, its "
      "carried actions and why each lands where it does, every deduplicated step edge, each unit's in-unit order, "
      "scoped tests, gate and hardware rounds). Built by `audit/sweeps/ac_order.py --write` from the M files, the "
      "action files' Depends slots and C.md's hardware inventory; rerunning it reproduces this file's numbers.")
    w("")
    w("## 1. What a step is, and where it lands")
    w("")
    w("A **step** is (merged change, unit): the part of one change that lands in one unit. A constituent action's part lands, "
      "in this priority:")
    w("")
    w("1. **Non-edits carry nothing**: a From entry marked read, holds, blast-only, superseded, withdrawn, dropped or void "
      "makes no step (M.TSC.183/.225, which create nothing, have no step at all).")
    w("2. **Its own unit** — the unit of its ID (`A.U10.x` → U10; `A.U36a/b` → U36; `A.C.x` → C; `A.SDEP.x` → U0R, U0's "
      "dependency-refresh step after the B0 baseline, and `A.SDEP.25` → U37; `A.S0930.x` → the unit SUPP_owner_0930 "
      "states: .01/.02/.10/.11 U20, .09/.18 U19, .12-.16/.31-.33 U11, .17 U16, .03/.19-.26/.34-.37 U24, .04/.27/.38 U25, "
      ".05/.06/.28/.29/.39/.40 U26, .07/.08/.30/.41 U36). This holds whenever the Unit slot names that unit, and also for a "
      "code or test site whose Unit slot names a later unit only (an **implicit step**): every action was planned with "
      "its blast closed inside its own unit, so deferring a rename, signature or fake to a later unit would leave the "
      "unit gates in between red.")
    w("3. **The Unit slot's next unit** for a doc site (every site file `.md`) or a site born in a later unit (`(new)`): "
      "docs consolidate where the merge put them (B4 is U36) and a new file cannot be edited before it exists.")
    w("4. **A stated relocation**: a Unit slot or action text that lands a part elsewhere in words "
      f"({len(RELOC)} per-change relocations, {len(PULLS)} action pulls: `RELOC`/`PULLS` in the script), and the "
      "Unit slots that land each row with its own action (M.DOCS.024/.064/.066, M.SPEC.156).")
    w("5. **Dependency deferral**: a part never lands before a part it needs. An action's Depends entries were read "
      "one by one where they point at a later unit "
      f"({c['action_depends_to_a_later_unit']['pairs']} of {c['action_depends_refs']:,} references): co-landing and "
      "same-site notes do not order (the merges carry them); "
      f"{len(DEP_RULINGS)} entries were ruled by reading their text (`DEP_RULINGS`). Then every "
      "holder of an action waits for the first landing of what it needs, and a blast edit waits for its cause, to a fixed "
      "point. Each resulting deferral is written into the change's Unit slot with a ledger note (section 3).")
    w("")
    w("The Unit slot therefore names a change's completing unit and its explicit stages; the step list here also holds "
      "the implicit steps of rule 2, which the M files do not repeat (the executor applies that unit's original action "
      "text to the site, and the merged end state at the completing step).")
    w("")
    w("## 2. Counts")
    w("")
    nimp = sum(u["implicit_steps"] for u in units)
    w(f"- Merged changes: {c['changes']} (1,865 in the M files plus {c['changes'] - 1865} the A-C3 reports propose, "
      "placed now with the IDs they propose: AC3_S M.GEN.064, M.SRC_CORE.132, M.SRC_SENS.093, the eight S-05 "
      "docstring changes, M.HW_BENCH.137, M.TEST_UNIT.341, M.TWIN.166, M.DOCS.109 (= AC3_R R-04's doc change), "
      "M.PROC.046/.047; AC3_R R-04's run change as M.PROC.R04, ID pending). Changes with no step: "
      f"{', '.join(c['no_step_changes'])}.")
    w(f"- Steps: {c['steps']} ({c['steps'] - nimp} named by their Unit slot, {nimp} implicit per rule 2) in "
      f"{len(units)} units.")
    w(f"- Edges (deduplicated step pairs): {c['edges']:,}; by kind: " +
      ", ".join(f"{k} {v:,}" for k, v in sorted(c['edge_kinds'].items())) +
      ". `action` = an action-level Depends; `blast` = a blast edit after its cause; `dep-A`/`dep-M` = a change's Depends "
      "slot; `sweep` = a whole-tree sweep after the per-file changes it completes.")
    w(f"- Violations (an edge from a later step) after the fixes: {len(c['violations_remaining'])}. Dependency deferrals: "
      f"{c['deferrals']}. Co-landing groups inside a unit: {len(c['in_unit_cycles'])}. Lower-priority in-unit edges "
      f"dropped because they closed a cycle: " + ", ".join(f"{k} {v}" for k, v in sorted(c['in_unit_edges_dropped_to_break_cycles'].items())) + ".")
    w(f"- Unit and Depends edits written into the M files: {len(notes)} (each with a row in its file's "
      "\"## A-C2 order notes\" table).")
    w("")
    w("## 3. Checks and fixes")
    w("")
    w("### 3.1 Edges from a later step")
    w("")
    w("The coarse change-level parser reported 1,430 back edges and a giant cycle because it resolved every A-ID to whole "
      "changes. At step level the findings were:")
    w("")
    fw = c["action_depends_to_a_later_unit"]
    w(f"- **Action-level dependencies on a later unit** (the action files' own Depends): {fw['pairs']} pairs, read one by "
      "one: " + ", ".join(f"{k} {v}" for k, v in sorted(fw['after_reading'].items())) + " (`ign` = a co-landing, same-site, "
      "split-ownership, duplicate or settled-by note; `doconly` = only the doc holders wait; `inchange` = only inside a "
      "change that carries both). The genuine ones defer the dependent "
      "part (rule 5), the main groups being: the six driver renumberings A.U2.10/.12/.13/.14/.15/.17 and the catalog "
      "test A.U2.02 land in U3 with the persisted/printed split they need (A.U3.02/.05/.07); A.U2.21/.24/.25 in U6 "
      "(generated definitions, composed mock data); A.U9.09 in U10 (`TickSeconds`, A.U10.02); A.U10.R01's ladder in U13 "
      "(`I2C.clear()`/`recover()`, A.U13.R01); A.U10.09's A.2 text in U11; A.U10.28's shared lines in U16 (A.U16.18 "
      "first); the SystemService command gate, watchdog takeover and shutdown sequence A.S0930.12-.14, .31-.33 in U20 "
      "(they need A.U20.06's `supervise_tasks()`/`self._tasks` and the U16 erase); A.U24.47/.53/.65/.70 in U25 (the twin "
      "fault shape, `--config-dir`, the device helper); A.S0930.19/.34 in U26 (A.U26.71's guard derivation); "
      "A.U8C.121 in U8C2; A.U37.15/.16 in phase D (after A.C.11); the docs A.U14.R01 and A.U14.30 wait for the "
      "mechanisms they describe. Blast edits of a deferred action follow it.")
    w("- **Depends-slot edges from a later step**: 31 after the step model, each fixed in its M file (table 3.4): "
      "12 changes gain a stage at the unit of what they need (the test keeps its HEAD-form double until the shared "
      "helper lands: M.TEST_UNIT.137/.161/.204/.208/.225/.303, M.TSC.093/.119/.202; M.GEN.033's U20 forms; M.SPEC.007's "
      "U28 pointer; M.TEST_UNIT.056's U14 timeout cases), and 12 Depends texts are corrected: a wrong target "
      "(M.TEST_UNIT.173/.175 → M.TEST_HELP.018), a placeholder (M.TEST_UNIT.286's `M.SRC_NET.0xx` → .074/.091), and "
      "references that are not prerequisites, now marked `[follows]` (M.SRC_SENS.008, M.TEST_UNIT.056, M.PROC.027, "
      "M.SCR.009, M.SRC_NET.042, M.SRC_CORE.035, M.SRC_CORE.080, M.TEST_UNIT.247, M.TWIN.019).")
    w("- **The 7 changes with no Unit slot**: M.PROC.044 (\"phase D.\") and M.SCR.060 (\"S0930.\") had units the coarse "
      "parser could not read (D; U25 per AC3_R R-08 (h)); M.SRC_CORE.131 → U35 (M.SRC_CORE.116's unit); M.TSC.168 → U28 "
      "and M.TSC.174 → U36 (check-only steps at the latest read constituent's unit); M.TSC.183/.225 → \"none\" (nothing is "
      "created).")
    w("- **Unknown reference `M.SRC_NET.000`** (M.TEST_UNIT.286): the text read `M.SRC_NET.0xx`; it names the WiFi "
      "snapshot, M.SRC_NET.074 and .091 (A.U18.33), now written so.")
    w("- **\"S0930\" as a unit** (AC3_R R-08 (h)): M.SCR.054/.059/.060 → U25 and M.SCR.061 → U27 as Part R proposes; the "
      f"other {sum(1 for n in notes if n[3] == 'AC3_R R-08 (h)')} Unit slots naming an S0930 stage gain a line placing "
      "each A.S0930 part in its supplement unit.")
    w("")
    w("### 3.2 Cycles")
    w("")
    w("- **M.TWIN.019 ↔ .033**: the RTC (.033) reads the wall clock's `installed()` (.019), and .019's Depends named .033 "
      "for that same fact, reversed; corrected to `[follows]`. The action-level edge A.U25.71 → A.U25.20 still runs both "
      "ways between the two files, so they land as one U25 commit (M.TWIN.019's Depends says so).")
    w("- **M.DOCS.008 ↔ .011**: the VOC licence entry and the image notice refer to each other (A.U34.04 ↔ A.U34.09); "
      "one U34 commit (noted in both Depends slots).")
    w(f"- **No cycle crosses units.** Inside units, {len(c['in_unit_cycles'])} groups of steps depend on each other at "
      "action level (the largest: the U0R refresh families, the U25 host-side twin harness move, the U26 bench "
      "rewrite, the U36 doc pass); each group is one commit of its unit, and its members' order inside the commit is the "
      "merged changes' own. In U0R the groups run in SUPP_deps family order, one family per commit (A.SDEP.01). Depends "
      "and blast edges that would close a cycle are dropped from the in-unit order only (they stay satisfied: both ends "
      "land before the unit's gate).")
    w("")
    w("### 3.3 Fixed constraints")
    w("")
    w("- **U0's dependency refresh follows the B0 baseline and precedes every B1 change** (LEAD/R33, OR129.a): U0R is its "
      "own step after U0 (the baseline A.U0.02/.03/.04/.06 and the U0 doc pass) and before U1; every code, pin and tooling "
      "part of the refresh lands in U0R. Doc parts recording the refresh's outcomes land where their doc changes complete "
      "(rule 3), and the second check A.SDEP.25 runs in U37. AC3_S's M.GEN.064 (freezefs re-vendor) is a U0R step.")
    w("- **Private UART names from U10 onward** (AC_NOTES 48): every A.U10.35 part in `src/asy_uart_comm.py` and "
      "`src/asy_uart_link_driver.py` and the B39 changelog row (M.DOCS.024) land in U10; `UART`'s `txbuf` is born in U13 as "
      "`self._txbuf` (M.SRC_NET.192, .195) and `UARTLinkDriver`'s U17 work (M.SRC_NET.213/.215) uses `_role`. AC3_S's "
      "M.PROC.046 runs each U10 rename/privatisation sweep once over the whole tree after its per-file changes, still in U10.")
    w("- **A.U14.17 (a)'s boot bus clear lands in U13** with A.U13.R01 (M.SRC_SENS.008/.009 call it from `I2C.__init__`), "
      "so its generated call (M.GEN.005), the unit fakes (M.TEST_HELP.012) and the twin `Pin` (M.TWIN.021) land there too.")
    w("")
    w("### 3.4 Unit and Depends edits written into the M files")
    w("")
    w("| M-ID | slot | reason |")
    w("|---|---|---|")
    agg = collections.OrderedDict()
    for k, slot, ed, reason in notes:
        agg.setdefault((k, slot), []).append(reason)
    for (k, slot), rs in agg.items():
        w(f"| {k} | {slot} | {'; '.join(sorted(set(rs)))} |")
    w("")
    w("### 3.5 Recorded, standing")
    w("")
    split = [a for a, hs in R["H"].items()
             if len({u for k, u in hs if not ch[k]["doc"] and "site born" not in R["why"][(k, a)]}) > 1]
    born = sum(1 for (k, a), why_ in R["why"].items() if "site born" in why_ and not ch[k]["doc"])
    w(f"- Code or test parts of the same action landing in different units by an explicit merge decision ({len(split)} "
      "actions, e.g. "
      "A.U11.10's `run_setups()` in U11 while the generated batch removal co-lands in U20; A.U10.11/A.U11.16's `_read()` "
      "halves pulled into U16's rewrite): each is the merge's stated choice and leaves every unit's tree consistent.")
    w(f"- {born} code or test parts on a site born in a later unit land when the site exists (rule 3).")
    w("")
    w("### 3.6 A-C3 inputs folded in (the lead applies their body text)")
    w("")
    w("- **AC3_R R-08 (h)** applied: M.SCR.054/.059/.060 → U25, M.SCR.061 → U27; every other Unit slot naming an S0930 "
      "stage gains a line placing each A.S0930 part in its supplement unit (table 3.4).")
    w("- **AC3_R R-08 (a)-(g)** checked against the order: (a) agrees — A.U1.26's comment lands with M.TEST_UNIT.211 in "
      "U18; (b) **differs** — A.U28.12's A.3 pointer lands in U28 (A-C2 stage of M.SPEC.007), because M.SPEC.033/.034 "
      "depend on it there, so G8/R49's State should read \"A.3 list in U28 (M.SPEC.007's U28 stage)\"; (c) agrees — "
      "A.U24.34/.36/.37 travel host-side in U25 inside M.TEST_HELP.033 (their parts in other files land in U24); (d) agrees "
      "— A.U24.74 bites in U12 with the race fix, U35 completes M.TEST_UNIT.236; (e) **partly** — K.28's product gap fill "
      "lands in U11 (M.SRC_CORE.063) but its test lands in M.TEST_UNIT.290's U24 stage, with A.U24.39 on the same lines, "
      "and the per-row checklist in U35 (M.PROC.022), so LEAD/R24's State should say \"K.28 in U11 (M.SRC_CORE.063) and "
      "U24 (M.TEST_UNIT.290)\"; (f) agrees — the L2 halves land in U25 (M.TWIN.146); (g) agrees — the rungs land in U10, "
      "U13, U15-U18.")
    w("- **AC3_R R-01, R-02, R-06**: M.PROC.022 carries A.U35.03/.04/.05/.08/.09/.15/.22/.23/.28/.35/.37/.41/.50/.51 in U35 "
      "(the same set as AC3_S S-17); M.PROC.021 carries A.U32.05 in U32; M.PROC.003 (5a), the namespace proof, runs in U0 "
      "after the baseline, and the test schedule (section 4) waits on it.")
    w("- **AC3_R R-04 = AC3_S S-13**: M.DOCS.109 (the integrate-module skill file) in U36 after M.SPEC.142/.046; the "
      "baseline-run change (ID pending, `M.PROC.R04` here) in U36 after M.DOCS.109.")
    w("- **AC3_S new changes**: M.GEN.064 (freezefs re-vendor) in U0R; M.SRC_CORE.132 and M.SRC_SENS.093 (D.15 order) "
      "in U10, each after every other U10 step on its files; the eight S-05 docstring changes (M.GEN.065, M.SCR.075, "
      "M.TSC.228, M.TEST_HELP.068, M.TEST_UNIT.340, M.TWIN.165, M.HW_BENCH.136, M.HW_DEV.158) in U10; M.HW_BENCH.137 in "
      "U20; M.TEST_UNIT.341 and M.TWIN.166 in U24 after A.U24.49; M.PROC.046 in U10 after every per-file step of "
      "A.U10.18/.35/.37/.38/.40/.43/.44 (one sweep each, before U11); M.PROC.047 in U36 after M.TSC.044/.064. "
      "AC3_S's From completions (S-02, S-03, S-08-S-12, S-14, S-16, S-17 and its section 4) are placed as constituents of "
      "the changes they name; the only one that moves a part is S-14 (A.S0930.34 (4) in M.TSC.165 lands in U26, noted).")
    w("- **AC3_R R-03** proposes M.SRC_CORE.108's Unit → \"— (no step)\" with its body; left for the lead with the body "
      "(the order then loses that change's U13 step only).")
    w("")
    w("## 4. Test schedule (LEAD/R34, OR134.a)")
    w("")
    w("Inside a unit, in its in-unit order: after each step (or co-landing group), run the **scoped tests** of that "
      "step: the test files its Site and Blast name, plus the tests that import or name each touched file "
      "(`work_order.json` lists them per unit). MicroPython files run through the exact command `scripts/test.sh`'s "
      "`run_test_file` uses (same heap, `MICROPYPATH`, `TZ=UTC`), at both GC stages for a `src/` change; `tests_scripts` "
      "files through `uv run pytest <files>`; `tests_js` files through `npx vitest run <files>`. Then the unit closes on "
      "the **full gate** on its final tree, unchanged:")
    w("")
    for g in GATE:
        w(f"- {g}")
    w(f"- {COVERAGE}")
    w("")
    w("**Parallelism.** (1) Until U0 proves network-namespace isolation (M.PROC.003 (5a), AC3_R R-06), every port-binding "
      "suite (the unit tier at either GC stage, each twin device run, the web tier's test runs, coverage) runs one after "
      "another; lint and typecheck run beside them. Once proven, each port-binding suite gets its own namespace and the "
      "whole gate runs at once, bounded by local cores. (2) Each pushed unit lets GitHub CI run the full job matrix as a "
      "parallel lane (including `firmware-build-verify`), while the local gate runs. (3) A unit's full gate runs in the "
      "background on a worktree snapshot of its final tree while agents continue on the next unit; a red result is fixed "
      "forward as a delta before the next unit's own gate. (4) **No later unit is independent** of an earlier one by the "
      "criterion (no shared site file and no edge): every unit shares a site file (SPECIFICATION.md, CLAUDE.md, BACKLOG.md, "
      "`tests/machine.py`, …) or an edge with each later unit with steps, so units do not run on parallel worktrees. "
      "Ignoring doc files, a few far pairs would qualify (e.g. U12 with U21/U22/U29/U33; U9 with U12/U13; U3 with U21); "
      "using them would need the lead to rebase the doc steps serially, which this order does not plan. Agent "
      "parallelism stays at OR107's limit.")
    w("")
    w("**Tooling units** (U0/U0R, U7, U21, U27, U28, U37 and any unit touching `pyproject.toml`, `scripts/`, "
      "`toolchain/versions.toml`) add their BACKLOG chroot-list entry (CLAUDE.md \"Build-environment verification\").")
    w("")
    w("| unit | steps (named + implicit) | actions | co-landing groups | scoped test files | coverage run | hardware rounds that exercise it |")
    w("|---|---|---|---|---|---|---|")
    for u in units:
        cl = sum(1 for g in u["order"] if len(g) > 1)
        cov = "yes" if COVERAGE in u["full_gate"] else "—"
        hr = ", ".join(u["hardware_rounds"]) or "—"
        w(f"| {u['unit']} | {u['steps']} ({u['explicit_steps']} + {u['implicit_steps']}) | {u['actions']} | {cl} | "
          f"{len(u['scoped_tests'])} | {cov} | {hr} |")
    w("")
    w("## 5. Hardware rounds and sessions")
    w("")
    w("No unit runs anything against hardware: every hardware duty is a phase-C round after U37 (C.md), each under the "
      "owner's go-ahead given in that round's own conversation. The table above names, per unit, the rounds whose "
      "inventory rows (C.md H08-H83) exercise that unit's actions; a unit's changes are proven on silicon only there. "
      "Grouped into as few owner-approved sessions as the rounds' own dependencies allow:")
    w("")
    w("1. **Session 1 — R0, R1, R2, R3, R5, R4** in one conversation: R0 needs no board; R1's clean default run is the "
      "same-image, same-conversation precondition of R2 (owner at the bench), R3 (gated wear) and R5 (soak); R4's reflash "
      "rows change the image, so they run last and restore the standard image (A.C.01 (7), A.C.06). Each round's findings "
      "pass A-C as a delta (A.C.10); a fixed image re-runs the affected rows inside the same conversation.")
    w("2. **Session 2 — R6**, the 12.4-day rollover on the release-candidate image after R5, the board touched by nothing "
      "else (A.C.08); it may run as session 1's tail if the owner keeps that conversation open (then two sessions in all).")
    w("3. **Session 3 — R7**, the release proof, only after every phase-C delta is applied and one re-verification pass is "
      "green (A.C.09, A.C.11).")
    w("")
    w("A hardware row that needs the owner's push access to `hundertvolt/datasheets` is not one of these: that is an owner "
      "step before U28 (below).")
    w("")
    w("## 6. Needing the owner")
    w("")
    w("- **Push access to the private `hundertvolt/datasheets` repository before U28** (AC_NOTES 37; M.PROC.018, A.U28.35 "
      "the move, and M.DOCS' U34/U36 sections that describe it). Without it the move and its two doc sections are not "
      "executed; the rest of the order is unaffected.")
    w("- **Three hardware go-aheads** (section 5), R2 with the owner at the bench.")
    w("- No ordering question is open: every finding above was settled by an action's own text, a register or owner row, "
      "or a merge's stated Unit choice. Two placements the owner may notice in the review: the six driver renumberings "
      "land in U3 with the log-split they depend on (B1 keeps U2 for the catalog itself), and the system-command code "
      "(\"Reset to defaults\", \"Erase FRAM\", reboot/bootloader on the sequence) lands in U20, not U11, because it "
      "needs U20's supervisor split.")
    w("")
    w("## 7. In-unit order")
    w("")
    w("Per unit, the steps in order; `[a b]` is a co-landing group (one commit). The actions each step carries and "
      "why each lands there are in `work_order.json` (`steps`).")
    w("")
    for u in units:
        parts = []
        for g in u["order"]:
            parts.append(g[0] if len(g) == 1 else "[" + " ".join(g) + "]")
        w(f"**{u['unit']}** ({u['steps']}): " + ", ".join(parts))
        w("")
    open(f"{OUT}/WORK_ORDER.md", "w").write("\n".join(L).rstrip() + "\n")


if __name__ == "__main__":
    _wo, _R = main(write="--write" in sys.argv)
    if "--write" in sys.argv:
        render_md(_wo, _R)
