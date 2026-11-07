"""Dump every comment and docstring line of the given files as 'path:line: text' (read-only)."""
import ast, io, re, sys, tokenize

def py(path, src):
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                out.append((tok.start[0], tok.string))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        pass
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list):
                for st in body:
                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                        for i, ln in enumerate(src.splitlines()[st.lineno - 1:st.end_lineno]):
                            out.append((st.lineno + i, ln.strip()))
    except SyntaxError:
        pass
    return out

def generic(path, src):
    out, in_block = [], False
    hash_style = not path.endswith((".js", ".mjs", ".ts", ".css", ".jsonc"))
    for n, ln in enumerate(src.splitlines(), 1):
        s = ln.strip()
        if path.endswith((".html", ".md")):
            if "<!--" in s or in_block:
                out.append((n, s)); in_block = "-->" not in s
            continue
        if in_block:
            out.append((n, s)); in_block = "*/" not in s; continue
        if "/*" in s and not hash_style:
            out.append((n, s)); in_block = "*/" not in s.split("/*", 1)[1]; continue
        if not hash_style and re.search(r"(^|\s)//", s):
            out.append((n, s)); continue
        if hash_style and re.search(r"(^|\s)#(?![!{\[])", s):
            out.append((n, s))
    return out

for path in sys.argv[1:]:
    try:
        src = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        continue
    rows = py(path, src) if path.endswith(".py") else generic(path, src)
    for n, t in sorted(set(rows)):
        print(f"{path}:{n}: {t}")
