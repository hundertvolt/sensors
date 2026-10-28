"""Function-level census of src/ between two extracted trees: status, size and mechanism shapes per function.

Usage: python3 -I census.py BASE_DIR HEAD_DIR OUT_DIR. Read-only on both trees; writes funcs.tsv and families.tsv.
"""
import ast
import hashlib
import os
import sys
from collections import defaultdict

RENAMES = {"asy_base_classes.py": "base_classes.py", "asy_system_service.py": "system_service.py",
           "asy_config_manager.py": "config_manager.py", "asy_print_log.py": "print_log.py",
           "asy_api_response.py": "api_response.py", "asy_crc_checks.py": "crc_checks.py",
           "asy_captive_dns.py": "captive_dns.py", "asy_framing_codecs.py": "framing_codecs.py"}
TIME_CALLS = {"ticks_ms", "ticks_diff", "ticks_add", "ticks_us", "time", "mktime", "gmtime", "localtime"}
WAIT_CALLS = {"sleep", "sleep_ms", "wait_for", "wait_for_ms", "wait"}
TASK_CALLS = {"create_task", "Timer", "init", "schedule", "gather"}
LOG_HINTS = ("log", "report_if_fatal", "print")


def call_name(node):
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def body_lines(src_lines, node):
    """Non-comment, non-blank, non-docstring source lines of a def."""
    doc = set()
    body = getattr(node, "body", [])
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
        doc = set(range(body[0].lineno, body[0].end_lineno + 1))
    out = []
    for i in range(node.lineno, node.end_lineno + 1):
        if i in doc:
            continue
        s = src_lines[i - 1].strip()
        if s and not s.startswith("#"):
            out.append(s.split("  #")[0].rstrip())
    return out


def shapes(node, inner_defs):
    d = defaultdict(int)
    flags, excs, raises, consts = set(), set(), [], set()
    for n in ast.walk(node):
        if n is not node and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n in inner_defs:
            continue
        if isinstance(n, ast.Try):
            d["try"] += 1
            for h in n.handlers:
                t = h.type
                if t is None:
                    excs.add("bare")
                else:
                    for e in (t.elts if isinstance(t, ast.Tuple) else [t]):
                        excs.add(e.id if isinstance(e, ast.Name) else (e.attr if isinstance(e, ast.Attribute) else "?"))
        elif isinstance(n, ast.Raise):
            d["raise"] += 1
            if n.exc is not None and isinstance(n.exc, ast.Call) and n.exc.args and isinstance(n.exc.args[0], ast.Constant):
                raises.append(str(n.exc.args[0].value)[:50])
        elif isinstance(n, ast.While):
            d["while"] += 1
        elif isinstance(n, ast.If):
            d["if"] += 1
        elif isinstance(n, ast.Call):
            c = call_name(n)
            if c == "isinstance":
                d["isinstance"] += 1
            if c in TIME_CALLS:
                d["time"] += 1
            if c in WAIT_CALLS:
                d["wait"] += 1
            if c in TASK_CALLS:
                d["task"] += 1
            if c == "report_if_fatal":
                d["fatal"] += 1
            if any(h in c.lower() for h in LOG_HINTS):
                d["log"] += 1
        elif isinstance(n, ast.Assign):
            for tgt in n.targets:
                if isinstance(tgt, ast.Attribute) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, bool):
                    flags.add(tgt.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool) and abs(n.value) >= 100:
            consts.add(n.value)
    return d, flags, excs, raises, consts


def defs(path):
    try:
        src = open(path).read()
    except FileNotFoundError:
        return {}
    tree = ast.parse(src)
    lines = src.splitlines()
    out = {}

    def walk(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.ClassDef):
                walk(ch, prefix + ch.name + ".")
            elif isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                q = prefix + ch.name
                inner = {x for x in ast.walk(ch) if x is not ch and isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))}
                bl = body_lines(lines, ch)
                out[q] = (ch.lineno, bl, shapes(ch, inner))
                walk(ch, q + ".")
    walk(tree, "")
    mod = [s for s in (l.strip() for l in lines) if s and not s.startswith("#")]
    out["<module-consts>"] = (0, [l for l in mod if "const(" in l and "=" in l], (defaultdict(int), set(), set(), [], set()))
    return out


def main():
    base, head, outd = sys.argv[1:4]
    rows, fam = [], defaultdict(list)
    for fn in sorted(os.listdir(os.path.join(head, "src"))):
        if not fn.endswith(".py"):
            continue
        old = defs(os.path.join(base, "src", RENAMES.get(fn, fn)))
        new = defs(os.path.join(head, "src", fn))
        for q in sorted(set(old) | set(new)):
            o, n = old.get(q), new.get(q)
            ob = o[1] if o else []
            nb = n[1] if n else []
            if o and n:
                st = "same" if hashlib.sha1("\n".join(ob).encode()).digest() == hashlib.sha1("\n".join(nb).encode()).digest() else "changed"
            else:
                st = "new" if n else "removed"
            sd = n[2] if n else (defaultdict(int), set(), set(), [], set())
            so = o[2] if o else (defaultdict(int), set(), set(), [], set())
            keys = ("try", "raise", "isinstance", "if", "while", "time", "wait", "task", "fatal", "log")
            delta = " ".join(f"{k}{sd[0][k] - so[0][k]:+d}" for k in keys if sd[0][k] - so[0][k])
            newflags = sorted(sd[1] - so[1])
            newexc = sorted(sd[2] - so[2])
            newraise = sorted(set(sd[3]) - set(so[3]))
            newconst = sorted(sd[4] - so[4])
            if q == "<module-consts>":
                added = sorted(set(nb) - set(ob))
                removed = sorted(set(ob) - set(nb))
                rows.append((fn, q, "consts", len(ob), len(nb), f"+{len(added)} -{len(removed)}", "", "", "", ""))
                for a in added:
                    fam["const"].append(f"{fn}\t{a[:110]}")
                continue
            if st == "same":
                continue
            ln = n[0] if n else o[0]
            rows.append((fn, q, st, len(ob), len(nb), delta, ",".join(newflags), ",".join(newexc), " | ".join(newraise), ",".join(str(c) for c in newconst)))
            for f in newflags:
                fam["flag"].append(f"{fn}\t{q}\t{f}")
            for e in newexc:
                fam["except"].append(f"{fn}\t{q}\t{e}")
            for r in newraise:
                fam["raise"].append(f"{fn}\t{q}\t{r}")
            for c in newconst:
                fam["number"].append(f"{fn}\t{q}\t{c}")
            if sd[0]["fatal"] > so[0]["fatal"]:
                fam["fatal"].append(f"{fn}\t{q}\t{sd[0]['fatal'] - so[0]['fatal']}")
            if sd[0]["time"] > so[0]["time"]:
                fam["time"].append(f"{fn}\t{q}\t{sd[0]['time'] - so[0]['time']}")
            if sd[0]["isinstance"] > so[0]["isinstance"]:
                fam["isinstance"].append(f"{fn}\t{q}\t{sd[0]['isinstance'] - so[0]['isinstance']}")
    with open(os.path.join(outd, "funcs.tsv"), "w") as fh:
        fh.write("file\tfunc\tstatus\tncnb_old\tncnb_new\tshape_delta\tnew_flags\tnew_excepts\tnew_raise_msgs\tnew_numbers\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    with open(os.path.join(outd, "families.tsv"), "w") as fh:
        for k in sorted(fam):
            for v in fam[k]:
                fh.write(f"{k}\t{v}\n")


main()
