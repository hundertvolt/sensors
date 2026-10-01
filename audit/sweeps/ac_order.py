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
        return "U37" if aid == "A.SDEP.25" else "U0"
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
        if re.search(r"(after|before|from|until|since)\s+$", pre):
            continue
        tok = {"phase C": "C", "phase D": "D", "B0": "U0"}.get(m.group(1), m.group(1))
        if tok == "S0930":
            out.extend(sorted({action_unit(a) for a, live, _ in cons if a.startswith("A.S0930")}, key=ukey))
            continue
        out.append(tok)
    return out


def norm_unit(u):
    return "U0" if u in ("B0", "U0R") else u


UNITS = [u for u in UNITS if u not in ("B0", "U0R")]
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
        c["live"] = [a for a, live, _ in c["cons"] if live]
        toks = unit_tokens(c["slots"]["Unit"], c["cons"])
        c["T"] = sorted(set(toks), key=ukey)
        c["main"] = toks[0] if toks else None
        files = paths_in(c["slots"]["Site"]) | heading_paths(c["section"])
        c["files"] = sorted(files)
        c["doc"] = bool(files) and all(p.endswith(".md") for p in files)
        c["new"] = bool(re.search(r"\(new\b|\bnew\)", c["section"] or "")) or c["slots"]["Site"].strip().lower().startswith("new")
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
            elif u in T:
                L[(k, a)], why[(k, a)] = u, "own unit, named in the Unit slot"
            elif all(ukey(t) < ukey(u) for t in T):
                L[(k, a)], why[(k, a)] = u, "own unit (the Unit slot writes it early in end form; confirmed in place here)"
            elif c["doc"] or c["new"]:
                t = min((t for t in T if ukey(t) > ukey(u)), key=ukey)
                L[(k, a)], why[(k, a)] = t, ("deferred to the next Unit-slot unit (doc site)" if c["doc"] else
                                             "deferred to the next Unit-slot unit (site born there)")
            else:
                L[(k, a)], why[(k, a)] = u, "own unit (implicit step: code/test site, blast closed in its unit)"
            if a in PULLS:
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
        st[k] |= set(c["T"])
        if not st[k]:
            st[k] = set()
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
                    ky, uy = min(cand, key=lambda t: ukey(t[1]))  # y's own change: its first landing
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
            if b not in H or b in c["live"]:
                continue
            cand = [(kb, ub) for kb, ub in own_holders(b, H, ch, act_files)
                    if kb != k and not (ch[kb]["doc"] and not c["doc"])]
            if cand:
                kb, ub = min(cand, key=lambda t: ukey(t[1]))
                tgt = next((u for u in mine if ukey(u) >= ukey(ub)), mine[-1])
                E.append(((kb, ub), (k, tgt), "dep-A", f"{k} Depends {b}"))
        for n, s, e in expand_m(dep):
            if n == k or n not in ch or not ST.get(n):
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
for _m in ("A.U10.R01", "A.U13.R01", "A.U15.R01", "A.U15.R02", "A.U15.R03", "A.U15.R04", "A.U16.R01", "A.U16.R02",
           "A.U16.R03", "A.U18.R01"):
    DEP_RULINGS[("A.U14.R01", _m)] = ("doconly", "F.2 and CLAUDE.md describe the mechanism once it exists")
# Parts that land outside their ID's unit by an action's own text.
PULLS = {
    "A.U28.13": ("U0", "A.SDEP.05: \"A.U28.13 (pulled forward)\" into the GitHub Actions pin refresh"),
    "A.U37.15": ("D", "its own title: \"Phase D: delete the plan and audit/\"; needs A.C.11"),
}
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
}


def rulings(D):
    ov = {}
    for a, l in D.items():
        for b, cls in l:
            if cls == "co":
                ov[(a, b)] = "ign"
    for k, (cls, _) in DEP_RULINGS.items():
        ov[k] = cls
    return ov
