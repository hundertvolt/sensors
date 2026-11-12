#!/usr/bin/env python3
"""One-time secret scan of a git dir's whole history (added lines, arduino/ excluded by pathspec): passes (a)-(f).
A found value is printed only once classified safe (placeholder, accepted default, no credential); else its shape.
Usage: nice -n 19 python3 -I sec_history_scan.py <git dir> [<tree rev, default e27b782>] [--contexts]"""

import gzip
import hashlib
import re
import subprocess
import sys
import threading
import time
import zlib
from collections import Counter, defaultdict
from fnmatch import fnmatch

PATHSPEC = ["--", ".", ":!arduino"]

# ---- classification by sha256[:8] of the value (never by value), filled from the masked runs ----
# c/b/e: accepted | bench-throwaway | placeholder | no-credential | real ; d: bench | placeholder | no-ssid | real
P, N, B = "placeholder", "no-credential", "bench-throwaway"
CLASSES: dict[str, tuple[str, str]] = {
    # (c)
    "07ab59f4": (N, "the 8-asterisk password mask"), "e0f0a9db": (P, "unit-test JSON fixture"), "122ccc25": (P, "README curl example"),
    "2984418a": (P, "mockdata fixture"), "ead195cc": (B, "REAL_PW of the deleted bench repro script"),
    "40b75a17": (N, "network.STAT_ constant name"), "297b0ba7": (N, "type annotation"), "fcf730b6": (P, "unit-test fixture"),
    "f0328b74": (N, "prose: the owner's quote"), "8f534896": (N, "the audit's redaction marker"), "e23bcd7b": (N, "prose"),
    "15e2b0d3": (P, "bound-check test value"), "08954250": (P, "unit-test fixture"), "ec4746f2": (P, "unit-test fixture"),
    "a493045d": (P, "unit-test fixture"), "79de26ab": (P, "JS test fixture (and its vitest log)"),
    "40a4ba15": (N, "type annotation"), "bc3f8f61": (N, "assertion text in a log"), "4c7c53dc": (N, "f-string template field"),
    "e2d7ec65": (N, "f-string template field"), "5e884898": (P, "the word 'password' as a twin/test value"),
    "a9d5b4be": (P, "unit-test fixture"), "2a424875": (N, "prose"), "425fec04": (N, "prose"),
    "3de0c68f": (P, "JS test fixture"), "2cdf9a98": (P, "unit-test fixture"), "8bf729f5": (P, "unit-test fixture"),
    "cb8aa5be": (N, "prose"), "d66e437d": (P, "JS test fixture"), "079c4020": (P, "JS test fixture"),
    "49000323": (P, "JS test fixture (and its vitest log)"), "68d92889": (P, "JS test fixture"), "4cfb53b4": (P, "JS test fixture"),
    "7751ef17": (N, "prose"), "f4a1197d": (N, "the key name HotspotPW"),
    "ab75b959": (B, "generated bench AP password (token_urlsafe(12)) in the deleted lockout handoff doc"),
    "cd927d54": (N, "code fragment 'password)'"), "ae387fbb": (N, "the attribute name autocomplete"),
    "a5c52a1c": (N, "a line-range reference"), "7ad0e43e": (N, "a path:line reference to the repro script"),
    # (b)
    "aad5a8ab": (P, "proxy URL with test userinfo on a .invalid host"), "b670eb5d": (N, "the scan's own pattern list"),
    "1caf8e22": (N, "the scan's own pattern list"), "9d8e3c88": (N, "the scan's own pattern list"), "34c770df": (N, "the scan's own pattern list"),
    "62249369": (P, "README usage example (xkcd phrase)"), "12eab4c5": (P, "the README example, quoted"),
    # (e) residuals, read in masked context: identifiers with part numbers, code names, a fixture path
    "c4b6935b": (N, "bus-topology name"), "7b1da7f1": (N, "datasheet file name"), "425bda52": (N, "code identifier"),
    "12b9478e": (N, "status field name"), "035b0f12": (N, "status field name"), "923ec921": (N, "status field name"),
    "9ef3267c": (N, "status field name"), "1edb062b": (N, "code identifier"), "dc2dca60": (N, "code identifier"),
    "e8f7a7f6": (N, "driver class name"), "f88efcae": (N, "error-path name"), "15fca56a": (N, "test class name"),
    "5f68f24c": (N, "bus-pairing name"), "8a7227f6": (N, "bus-pairing name"), "0dce1e14": (N, "bus-pairing name"),
    "b63d7b70": (N, "probe label"), "d97b6bf3": (N, "status field key"), "d6f6f0cc": (N, "USB by-id fixture path (its serial appears nowhere else)"),
    # (d)
    "45102d54": (P, "unit-test SSID"), "f04dda58": (P, "unit-test SSID"), "2b505597": ("no-ssid", "type annotation"),
    "5e0d5a36": (P, "unit-test SSID"), "8b5962b6": (P, "unit-test SSID"), "f5162206": ("no-ssid", "status word Valid"),
    "7d4a3a3b": (P, "unit-test SSID"), "d00df675": (P, "unit-test SSID"), "96c34a07": ("no-ssid", "status word Invalid"),
    "023279ec": (P, "unit-test SSID"), "8bda135a": (P, "the twin's own AP"), "18ff2ab6": (P, "twin test SSID"),
    "f0071b8d": (P, "twin test SSID"), "856255cb": (P, "twin CI SSID"), "24ad231b": (P, "mockdata SSID (synthetic dump)"),
    "a7fe8e31": (P, "mockdata SSID (synthetic dump)"), "031a8f0f": (P, "unit-test value"), "845c832a": (P, "toolchain test SSID"),
    "a4403ea9": (P, "toolchain test SSID"), "10119e4f": (P, "toolchain test SSID"), "b77bc011": ("bench", "the bench AP SSID"),
    "195c44d7": (P, "deliberately absent SSID"), "04801e8a": (P, "deliberately absent SSID"), "6d93a421": (P, "deliberately absent SSID"),
    "548f20d9": (P, "deliberately absent SSID"), "84207b0e": ("bench", "a generated bench AP SSID"), "33e6d73f": (P, "length-test filler"),
    "5a776d62": (P, "unit-test SSID"), "4a99557e": (P, "length-test filler"), "a95a422f": (P, "non-ASCII test SSID"),
    "2ff2451b": (P, "length-test filler"), "6c372dd3": (P, "unit-test SSID"), "884e7472": (P, "JS test SSID (vitest log)"),
    "4ea14058": (P, "JS test SSID"), "2d711642": (P, "length-test filler"), "740eaf82": ("no-ssid", "the generator's f-string template"),
    "69c5c12d": (P, "twin test SSID"), "a08a0fcb": (P, "twin test SSID"), "7063dece": ("no-ssid", "a variable name"),
    "daa3c580": (P, "MQTT PoC twin SSID"), "ccc77318": ("bench", "a generated bench AP SSID (deleted lockout doc)"),
    "b9776d7d": ("no-ssid", "prose"), "80c00e10": ("no-ssid", "prose"), "1785cfc3": ("no-ssid", "prose"), "dc937b59": ("no-ssid", "the word None"),
    "9a0808e6": (P, "README usage example SSID"), "ebcb7b97": ("no-ssid", "a metavar"), "bcfa236d": (P, "the README example SSID, quoted"),
}
EXPLICIT_SAFE = {"12345678": "accepted", "supersecret": P, "hunter2hunter2": P, "digital-twin-password": P}
PRINTABLE = {"accepted", P, N, "bench", "no-ssid"}
WITHHELD_TRACE = {B, "real", "unclassified"}

CODE_EXT = (".py", ".js", ".mjs", ".cjs", ".ts", ".json", ".html", ".css", ".pdf", ".toml", ".ini", ".lock", ".svg")

COMMIT_RE = re.compile(r"^@@([0-9a-f]{7,40}) (\d+)$")
HUNK_RE = re.compile(r"^(@@+) (?:-\d+(?:,\d+)? )+\+(\d+)(?:,\d+)? @@+")

# (b) token shapes: A.U29.04's list first, then the extension set (reported apart)
B_PLAN = [("gh-prefix", r"(?:ghp_|gho_|ghs_|github_pat_)"), ("aws-akia", r"AKIA[0-9A-Z]{16}"), ("slack-xox", r"xox[abp]-"),
          ("pem-private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), ("google-aiza", r"AIza[0-9A-Za-z_-]{35}"),
          ("sk-key", r"sk-[A-Za-z0-9]{20,}")]
B_EXT = [("gh-ur-token", r"gh[ur]_[A-Za-z0-9]{20,}"), ("slack-xox-rs", r"xox[rs]-"), ("sk-ant", r"sk-ant-[A-Za-z0-9_-]{20,}"),
         ("gitlab-pat", r"glpat-[A-Za-z0-9_-]{20}"), ("npm-token", r"npm_[A-Za-z0-9]{36}"), ("pypi-token", r"pypi-AgE[A-Za-z0-9_-]{20,}"),
         ("jwt", r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\."), ("bearer", r"(?i)bearer\s+[A-Za-z0-9._~+/-]{20,}"),
         ("url-userinfo", r"[a-zA-Z][a-zA-Z0-9+.-]{1,15}://[^/\s:@\"'<>]{1,64}:[^/\s@\"'<>]{1,128}@[A-Za-z0-9.-]")]
B_RES = [(n, re.compile(p), "plan") for n, p in B_PLAN] + [(n, re.compile(p), "ext") for n, p in B_EXT]
B_PREFILTER = ("ghp_", "gho_", "ghs_", "github_pat_", "akia", "xox", "private key", "aiza", "sk-", "ghu_", "ghr_", "glpat-", "npm_",
               "pypi-", "eyj", "bearer", "://")

# (c) A.U29.04's literal regex, then the extensions (c+), deduplicated by value against (c)
C_RE = re.compile(r"""(?i)(pass(word|wd)?|_pw|"pw"|psk|secret|token|api_?key)\W{0,3}[:=]\s*[bfr]?["']([^"']{8,})["']""")
C_PREFILTER = ("pass", "_pw", '"pw"', "psk", "secret", "token", "apikey", "api_key")
KEYW = r"(?:password|passwd|passwort|kennwort|passphrase|psk|pw|secret|token|credentials?)"
C_EXT = [  # (name, regex, value group, applies to code files)
    ("pw-suffix", re.compile(r"""(?i)(\w*pw|\w*passphrase|\w*credentials?|private_?key|wifi_?key|wpa_?key|passwort|kennwort)["']?\s{0,2}[:=]\s*[bfr]?["']([^"']{8,})["']"""), 2, True),
    ("unquoted-assign", re.compile(r"""(?i)\b(wpa_passphrase|passphrase|psk|password|passwd|pw)\s*=\s*([^\s"'`$\{<(\[,;&|]{8,})"""), 2, False),
    ("yaml-key", re.compile(r"""(?i)^\s*-?\s*(password|passwd|psk|passphrase|wpa_passphrase|secret|token)\s*:\s*([^\s"'`$\{<#]{8,})\s*$"""), 2, False),
    ("nmcli", re.compile(r"""(?i)(wifi-sec\.psk|\bpassword)\s+["']?([^\s"'$\{<]{8,})"""), 2, True),
    ("connect-positional", re.compile(r"""\.connect\(\s*[bfr]?["']([^"']+)["']\s*,\s*[bfr]?["']([^"']{8,})["']"""), 2, True),
    ("prose-quoted", re.compile(r"""(?i)\b(""" + KEYW + r""")\s{1,3}(?:is\s+|of\s+)?[`"']([^`"'\s]{8,})[`"']"""), 2, False),
    ("cli-flag", re.compile(r"""(?i)(--(?:password|passwd|psk|passphrase))[ =]["']?([^\s"'$\{<]{8,})"""), 2, True),
]
C_EXT_PREFILTER = ("--pass", "--psk", "pw", "passphrase", "credential", "private", "key", "password", "passwd", "passwort", "kennwort", "psk", "secret", "token", ".connect(")

# (d) A.U29.04's literal SSID regex, then extensions
D_RE = re.compile(r"""(?i)e?ssid\W{0,3}[:=]\s*["']([^"']+)["']""")
D_EXT = [
    ("bytes-prefix", re.compile(r"""(?i)e?ssid\W{0,3}[:=]\s*[bfr]["']([^"']+)["']"""), True),
    ("unquoted-assign", re.compile(r"""(?i)\be?ssid\s*[=:]\s*([^\s"'`$\{<(\[,;&|)\]}]{3,})"""), False),
    ("nmcli-connect", re.compile(r"""(?i)(?:wifi\s+connect|802-11-wireless\.ssid)\s+["']?([^\s"'$\{<]+)"""), True),
    ("connect-positional", re.compile(r"""\.connect\(\s*[bfr]?["']([^"']+)["']\s*,"""), True),
    ("prose-quoted", re.compile(r"""(?i)\bssid\s{1,3}(?:is\s+)?[`"']([^`"'\s]{3,})[`"']"""), False),
    ("cli-flag", re.compile(r"""(?i)--e?ssid[ =]["']?([^\s"'$\{<]{3,})"""), True),
]

# (e) A.U29.04's token class, plus long hex (the hash families)
E_RE = re.compile(r"[A-Za-z0-9+/_-]{16,}")
HEX_RE = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{32,}(?![0-9A-Za-z])")

# (f) MACs (A.U29.04's form, case-insensitive) plus the hyphen form; private IPv4
MAC_RE = re.compile(r"(?i)(?<![0-9a-f:])((?:[0-9a-f]{2}:){5}[0-9a-f]{2})(?![0-9a-f:])")
MAC_H_RE = re.compile(r"(?i)(?<![0-9a-f-])((?:[0-9a-f]{2}-){5}[0-9a-f]{2})(?![0-9a-f-])")
IP_RE = re.compile(r"(?<![\d.])((?:10|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d|\.\d)")

# (a) secret-shaped file names: A.U29.04's list, then extensions
A_PLAN = ["config_*.cfg", "*.env", "*.pem", "*.key", "*.p12", "*.nmconnection", "wpa_supplicant*", "secret*", "credential*"]
A_EXT = [".env.*", "*.pfx", "id_rsa*", "id_ed25519*", "*.keystore", "*.jks", ".netrc", ".npmrc", ".pypirc", "hostapd*.conf", "*.ovpn",
         "*.kdbx", "*.htpasswd", "*.crt", "*token*", "*passw*"]

QUOTED_RE = re.compile(r"""(["'`])([^"'`]{6,})\1""")
LONGTOK_RE = re.compile(r"[A-Za-z0-9+/=_-]{20,}")


def sha8(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8", "surrogatepass")).hexdigest()[:8]


def shape(v: str) -> str:
    cls = "".join(c for c, f in (("U", str.isupper), ("L", str.islower), ("D", str.isdigit)) if any(f(ch) for ch in v))
    if any(not ch.isalnum() and not ch.isspace() for ch in v):
        cls += "S"
    if any(ch.isspace() for ch in v):
        cls += "W"
    return f"len={len(v)} cls={cls} sha={sha8(v)}"


def transitions(tok: str) -> float:
    k = [("U" if c.isupper() else "L" if c.islower() else "D") for c in tok if c.isalnum()]
    return sum(1 for a, b in zip(k, k[1:]) if a != b) / max(len(k) - 1, 1)


def wordy(tok: str) -> bool:
    """True when a token is an identifier or path made of words, not a random string."""
    letters = []
    for seg in re.split(r"[/_+\-]+", tok):
        letters += [p for p in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", seg) if not p.isdigit()]
    if not letters:
        return False
    short = sum(1 for p in letters if len(p) <= 2)
    if sum(map(len, letters)) / len(letters) >= 3.0 and short / len(letters) <= 0.34:
        return True
    return transitions(tok) < 0.35


def is_code(path: str) -> bool:
    return path.lower().endswith(CODE_EXT)


def cls_of(v: str) -> tuple[str, str]:
    if v in EXPLICIT_SAFE:
        return EXPLICIT_SAFE[v], ""
    return CLASSES.get(sha8(v), ("unclassified", ""))


def safe_value(v: str) -> bool:
    return cls_of(v)[0] in PRINTABLE


class Rec:
    __slots__ = ("hits", "commits", "paths", "first", "keys", "ctx", "variant")

    def __init__(self, variant: str) -> None:
        self.hits = 0
        self.commits: set[str] = set()
        self.paths: Counter[str] = Counter()
        self.first: tuple[int, str, str, int] | None = None
        self.keys: set[str] = set()
        self.ctx = ""
        self.variant = variant

    def add(self, commit: str, ct: int, path: str, line: int, key: str, ctx: str) -> None:
        self.hits += 1
        self.commits.add(commit[:8])
        self.paths[path] += 1
        if key:
            self.keys.add(key.lower())
        if self.first is None or ct < self.first[0]:
            self.first = (ct, commit[:8], path, line)
            self.ctx = ctx


def e_family(tok: str, path: str, text: str, start: int) -> str:
    base = path.rsplit("/", 1)[-1]
    low = path.lower()
    before = text[max(0, start - 40):start]
    if base in ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "uv.lock") or re.match(r"sha(1|256|384|512)-", tok) or '"integrity"' in text:
        return "lockfile integrity hash"
    if low.endswith(".pdf") or low.startswith("datasheets/") or "dstxt" in low or "datasheet" in low:
        return "datasheet-derived text"
    if "session_" in tok or "claude.ai/code/session" in text or "Claude-Session" in text or re.search(r"session\W{0,3}$", before):
        return "Claude session id (commit trailer or session URL)"
    if before.endswith(("tmp.", "/tmp/", "tmp/")) or re.search(r"tmp\.[A-Za-z0-9]{6,}", text[max(0, start - 4):start + len(tok)]):
        return "mktemp name"
    if "/" in tok and all(len(s) <= 12 or wordy(s) for s in tok.split("/") if s):
        return "path or URL"
    if re.search(r"node_modules/\.|\?v=|CMakeFiles|GEN |\.c\.o|\.cmake", text):
        return "build or cache artefact name"
    if '"node_id"' in text or re.fullmatch(r"[A-Z]{1,4}_kw[A-Za-z0-9_-]+", tok):
        return "GitHub API node id (CI job JSON)"
    if re.search(r"(?i)cache (hit occurred|saved with key|key)", text):
        return "CI cache key"
    if "digital_twin" in low and "record" in low:
        return "twin-record hash"
    if text[start + len(tok):start + len(tok) + 1] == "=" or "base64" in text.lower() or "b64" in text.lower():
        return "base64 fixture"
    return ""


def hex_family(tok: str, path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    if base in ("package-lock.json", "uv.lock", "yarn.lock"):
        return "lockfile integrity hash (hex)"
    if len(tok) == 40:
        return "git object id (40 hex)"
    if len(tok) == 64:
        return "sha256 pin or digest (64 hex)"
    return f"other hex run ({len(tok)} hex)"


class Scan:
    def __init__(self) -> None:
        self.c: dict[str, Rec] = {}
        self.d: dict[str, Rec] = {}
        self.b: dict[tuple[str, str], Rec] = {}
        self.e_fam: Counter[str] = Counter()
        self.e_fam_distinct: dict[str, set[str]] = defaultdict(set)
        self.e_ident = 0
        self.e_resid: dict[str, Rec] = {}
        self.mac: dict[str, Rec] = {}
        self.ip: dict[str, Rec] = {}
        self.lines: Counter[str] = Counter()
        self.paths_seen: dict[str, tuple[int, str]] = {}
        self.paths_added: dict[str, tuple[int, str]] = {}

    def mask(self, text: str, keep: list[str]) -> str:
        out = text
        for v in sorted(set(keep), key=len, reverse=True):
            if len(v) >= 4 and not safe_value(v):
                out = out.replace(v, "<<V:" + sha8(v) + ">>")

        def q(m: re.Match[str]) -> str:
            inner = m.group(2)
            if inner.startswith("<<") or safe_value(inner):
                return m.group(0)
            return m.group(1) + f"<<q{len(inner)}:{sha8(inner)}>>" + m.group(1)
        out = QUOTED_RE.sub(q, out)
        out = LONGTOK_RE.sub(lambda m: m.group(0) if wordy(m.group(0)) else f"<<t{len(m.group(0))}>>", out)
        return out.strip()[:240]

    def line(self, commit: str, ct: int, path: str, ln: int, text: str, src: str) -> None:
        self.lines[src] += 1
        if not text:
            return
        low = text.lower()
        code = is_code(path)
        found: list[tuple[dict, object, str, str, str]] = []
        if any(p in low for p in B_PREFILTER):  # (b)
            for name, rx, kind in B_RES:
                for m in rx.finditer(text):
                    s, e = m.start(), m.end()
                    while e < len(text) and (text[e].isalnum() or text[e] in "_-"):
                        e += 1
                    found.append((self.b, (name, text[s:e]), kind, name, text[s:e]))
        cvals: set[str] = set()
        if any(p in low for p in C_PREFILTER):  # (c)
            for m in C_RE.finditer(text):
                cvals.add(m.group(3))
                found.append((self.c, m.group(3), "c", m.group(1), m.group(3)))
        if any(p in low for p in C_EXT_PREFILTER):
            for name, rx, g, in_code in C_EXT:
                if (code and not in_code) or (name == "nmcli" and "nmcli" not in low):
                    continue
                for m in rx.finditer(text):
                    v = m.group(g)
                    if v not in cvals:
                        cvals.add(v)
                        found.append((self.c, v, "c+" + name, m.group(1) if name != "connect-positional" else "connect()", v))
        if "ssid" in low or ".connect(" in low or "nmcli" in low:  # (d)
            dvals: set[str] = set()
            for m in D_RE.finditer(text):
                dvals.add(m.group(1))
                found.append((self.d, m.group(1), "d", "ssid", m.group(1)))
            for name, rx, in_code in D_EXT:
                if (code and not in_code) or (name == "nmcli-connect" and "nmcli" not in low):
                    continue
                for m in rx.finditer(text):
                    v = m.group(1)
                    if v not in dvals:
                        dvals.add(v)
                        found.append((self.d, v, "d+" + name, name, v))
        for m in E_RE.finditer(text):  # (e)
            tok = m.group()
            if not (any(ch.isupper() for ch in tok) and any(ch.islower() for ch in tok) and any(ch.isdigit() for ch in tok)):
                continue
            if wordy(tok):
                self.e_ident += 1
                continue
            fam = e_family(tok, path, text, m.start())
            if fam:
                self.e_fam[fam] += 1
                self.e_fam_distinct[fam].add(tok)
            else:
                found.append((self.e_resid, tok, "e", "", tok))
        for m in HEX_RE.finditer(text):
            fam = hex_family(m.group(), path)
            self.e_fam[fam] += 1
            self.e_fam_distinct[fam].add(m.group().lower())
        if found:
            ctx = self.mask(text, [f[4] for f in found])
            for store, key, variant, name, _v in found:
                rec = store.get(key)
                if rec is None:
                    rec = store[key] = Rec(variant)
                elif variant in ("c", "d", "plan"):  # a value any A.U29.04 regex found is filed under it
                    rec.variant = variant
                rec.add(commit, ct, path, ln, name, ctx)
        if text.count(":") >= 5 or text.count("-") >= 5:  # (f)
            for rx in (MAC_RE, MAC_H_RE):
                for m in rx.finditer(text):
                    v = m.group(1).lower().replace("-", ":")
                    self.mac.setdefault(v, Rec("f")).add(commit, ct, path, ln, "", "")
        if "10." in text or "172." in text or "192.168." in text:
            for m in IP_RE.finditer(text):
                if private_ip(m.group(1)):
                    self.ip.setdefault(m.group(1), Rec("f")).add(commit, ct, path, ln, "", "")


def private_ip(v: str) -> bool:
    o = [int(x) for x in v.split(".")]
    if any(x > 255 for x in o):
        return False
    return o[0] == 10 or (o[0] == 172 and 16 <= o[1] <= 31) or (o[0] == 192 and o[1] == 168)


def unquote_path(p: str) -> str:
    if p.startswith('"') and p.endswith('"'):
        return p[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
    return p


def diff_path(line: str) -> str:
    if line.startswith(("diff --cc ", "diff --combined ")):
        return unquote_path(line.split(" ", 2)[2])
    rest = line[11:]
    if rest.startswith('"'):
        parts = re.findall(r'"(?:[^"\\]|\\.)*"|\S+', rest)
        return unquote_path(parts[-1])[2:]
    n = (len(rest) - 5) // 2
    if (len(rest) - 5) % 2 == 0 and rest[2:2 + n] == rest[5 + n:]:
        return rest[5 + n:]
    return rest.split(" b/", 1)[-1]


def stream_patches(gd: str, emit) -> tuple[dict[str, tuple[int, str]], dict[str, tuple[int, str]]]:
    """A.U29.04's `git log --all -p --no-color --format=@@%h`, with --full-history (the default simplification prunes side
    branches a merge is TREESAME to) and each merge's own resolution lines (dense-combined)."""
    cmd = ["git", "-C", gd, "log", "--all", "--full-history", "-p", "--diff-merges=dense-combined", "--no-color", "--format=@@%h %ct", *PATHSPEC]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    assert proc.stdout is not None
    seen: dict[str, tuple[int, str]] = {}
    added: dict[str, tuple[int, str]] = {}
    commit, ct, path, in_hunk, npar, ln = "", 0, "", False, 1, 0
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace").rstrip("\n").rstrip("\r")
        if line.startswith("@@"):
            m = COMMIT_RE.match(line)
            if m:
                commit, ct, in_hunk = m.group(1), int(m.group(2)), False
                continue
            h = HUNK_RE.match(line)
            if h:
                npar, ln, in_hunk = len(h.group(1)) - 1, int(h.group(2)), True
                continue
        if line.startswith(("diff --git ", "diff --cc ", "diff --combined ")):
            in_hunk = False
            path = diff_path(line)
            seen.setdefault(path, (ct, commit))
            continue
        if not in_hunk:
            if line.startswith(("rename to ", "copy to ")):
                path = unquote_path(line.split(" ", 2)[2])
                seen.setdefault(path, (ct, commit))
            elif line.startswith("new file mode") and (path not in added or ct < added[path][0]):
                added[path] = (ct, commit)
            continue
        if line.startswith("\\"):
            continue
        pre = line[:npar]
        if "-" in pre:
            continue
        if pre == "+" * npar:
            emit(commit, ct, path, ln, line[npar:], "merge" if npar > 1 else "patch")
        ln += 1
    if proc.wait() != 0:
        sys.exit(f"git log exited {proc.returncode}")
    return seen, added


def cat_batch(gd: str, specs: list[str]) -> list[tuple[str, bytes | None]]:
    """git cat-file --batch with the request list written from a thread, so a full output pipe cannot deadlock it."""
    proc = subprocess.Popen(["git", "-C", gd, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    assert proc.stdin is not None and proc.stdout is not None
    stdin = proc.stdin

    def feed() -> None:
        stdin.write(("\n".join(specs) + "\n").encode())
        stdin.close()
    th = threading.Thread(target=feed)
    th.start()
    res: list[tuple[str, bytes | None]] = []
    for spec in specs:
        hdr = proc.stdout.readline().split()
        if len(hdr) < 3 or hdr[1] != b"blob":
            res.append((spec, None))
            continue
        res.append((spec, proc.stdout.read(int(hdr[2]))))
        proc.stdout.read(1)
    th.join()
    proc.wait()
    return res


def blob_list(gd: str) -> tuple[dict[str, tuple[int, str, str]], Counter[str]]:
    out = subprocess.run(["git", "-C", gd, "log", "--all", "--full-history", "--raw", "--no-abbrev", "--format=@@%h %ct", *PATHSPEC],
                         check=True, capture_output=True).stdout.decode("utf-8", "replace")
    blobs: dict[str, tuple[int, str, str]] = {}
    skipped: Counter[str] = Counter()
    commit, ct = "", 0
    for line in out.splitlines():
        m = COMMIT_RE.match(line)
        if m:
            commit, ct = m.group(1)[:8], int(m.group(2))
            continue
        if not line.startswith(":"):
            continue
        meta, _, p = line.partition("\t")
        new = meta.split()[3]
        p = unquote_path(p.split("\t")[-1])
        if set(new) == {"0"}:
            continue
        ext = p.rsplit(".", 1)[-1].lower() if "." in p else ""
        if ext in ("gz", "prof"):
            if new not in blobs or ct < blobs[new][0]:
                blobs[new] = (ct, commit, p)
        elif ext in ("pdf", "ico", "png", "jpg", "jpeg", "gif"):
            skipped[ext] += 1
    return blobs, skipped


def blob_lines(data: bytes, p: str) -> list[str] | None:
    if p.endswith(".gz"):
        try:
            return gzip.decompress(data).decode("utf-8", "replace").splitlines()
        except (OSError, EOFError, zlib.error):
            return None
    return [s.decode("ascii") for s in re.findall(rb"[\x20-\x7e]{6,}", data)]


def blob_pass(gd: str, blobs: dict[str, tuple[int, str, str]], emit) -> int:
    """gz logs and the profile: their text never reaches the patch stream, so the blobs themselves are read."""
    bad = 0
    for sha, data in cat_batch(gd, sorted(blobs)):
        ct, commit, p = blobs[sha]
        text = blob_lines(data, p) if data is not None else None
        if text is None:
            bad += 1
            continue
        for i, t in enumerate(text, 1):
            emit(commit, ct, p + "!blob", i, t, "blob")
    return bad


def message_pass(gd: str, emit) -> None:
    out = subprocess.run(["git", "-C", gd, "log", "--all", "--full-history", "--format=%x00%h %ct%n%B", *PATHSPEC], check=True, capture_output=True).stdout
    for chunk in out.decode("utf-8", "replace").split("\x00")[1:]:
        head, _, body = chunk.partition("\n")
        commit, ct = head.split(" ")
        for i, t in enumerate(body.splitlines(), 1):
            emit(commit, int(ct), "<commit message>", i, t, "message")


def tree_text(gd: str, rev: str, gz_paths: list[str]) -> dict[str, str]:
    out = subprocess.run(["git", "-C", gd, "grep", "-I", "-l", "--null", "--no-color", "-e", "", rev, *PATHSPEC],
                         capture_output=True).stdout
    names = [x.decode("utf-8", "replace").split(":", 1)[1] for x in out.split(b"\x00") if x.strip()]
    files: dict[str, str] = {}
    for spec, data in cat_batch(gd, [f"{rev}:{n}" for n in names]):
        if data is not None:
            files[spec.split(":", 1)[1]] = data.decode("utf-8", "replace")
    for spec, data in cat_batch(gd, [f"{rev}:{p}" for p in gz_paths]):
        lines = blob_lines(data, spec) if data is not None else None
        if lines is not None:
            files[spec.split(":", 1)[1] + "!blob"] = "\n".join(lines)
    return files


def day(ct: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ct))


def fmt_first(r: Rec) -> str:
    assert r.first is not None
    ct, c, p, ln = r.first
    return f"first {c} {day(ct)} {p}:{ln}"


def show(v: str) -> str:
    cls, note = cls_of(v)
    shown = repr(v) if cls in PRINTABLE else "(value withheld)"
    return f"[{cls}{(': ' + note) if note else ''}] {shape(v)} {shown}"


def main() -> None:
    gd = sys.argv[1]
    rev = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "e27b782"
    contexts = "--contexts" in sys.argv
    t0 = time.time()
    sc = Scan()
    sc.paths_seen, sc.paths_added = stream_patches(gd, sc.line)
    t1 = time.time()
    blobs, skipped = blob_list(gd)
    bad = blob_pass(gd, blobs, sc.line)
    message_pass(gd, sc.line)
    t2 = time.time()

    # literal trace: every occurrence of each withheld value, in any added line, blob line or message
    trace_vals = {v for v in sc.c if len(v) >= 8 and cls_of(v)[0] in WITHHELD_TRACE}
    trace_vals |= {v for v in sc.e_resid if CLASSES.get(sha8(v), ("",))[0] in (B, "real")}
    trace: dict[str, list[tuple[int, str, str, int, str]]] = defaultdict(list)

    def tr(commit: str, ct: int, path: str, ln: int, text: str, src: str) -> None:
        for v in trace_vals:
            if v in text:
                trace[v].append((ct, commit[:8], path, ln, sc.mask(text, list(trace_vals))))
    if trace_vals:
        stream_patches(gd, tr)
        blob_pass(gd, blobs, tr)
        message_pass(gd, tr)
    t3 = time.time()

    lit_a = subprocess.run(["git", "-C", gd, "log", "--all", "--diff-filter=A", "--name-only", "--format=", *PATHSPEC],
                           check=True, capture_output=True).stdout.decode("utf-8", "replace").split("\n")
    lit_a_set = {unquote_path(p) for p in lit_a if p}
    tree = tree_text(gd, rev, sorted({p for p in sc.paths_seen if p.endswith(".gz")}))
    big = "\n".join(tree.values())
    t4 = time.time()

    out = print
    out(f"# scan of {gd.rstrip('/').rsplit('/', 1)[-1]}; tree checks at {rev} ({len(tree)} text files incl. gz blobs)")
    out(f"lines scanned by source: {dict(sc.lines)}")
    out(f"blob pass: {len(blobs)} gz/prof blobs read, {bad} unreadable; not read (blob versions by type, vendor PDFs and icons): {dict(skipped)}")
    out(f"timing: patch stream {t1 - t0:.1f}s, blobs+messages {t2 - t1:.1f}s, literal trace {t3 - t2:.1f}s, tree load {t4 - t3:.1f}s")

    out("\n## (a) secret-shaped file names")
    out(f"literal --diff-filter=A paths: {len(lit_a_set)}; stream new-file paths: {len(sc.paths_added)}; stream destination paths: {len(sc.paths_seen)}")
    out(f"literal-not-in-stream: {sorted(lit_a_set - set(sc.paths_added))[:10]}; stream-not-in-literal: {sorted(set(sc.paths_added) - lit_a_set)[:10]}")
    for label, pats in (("plan", A_PLAN), ("ext", A_EXT)):
        for p in sorted(sc.paths_seen):
            base = p.rsplit("/", 1)[-1].lower()
            hit = [x for x in pats if fnmatch(base, x.lower())]
            if hit:
                ct, c = sc.paths_added.get(p, sc.paths_seen[p])
                out(f"  [{label}] {p} pattern={hit} first {c[:8]} {day(ct)} added={'yes' if p in lit_a_set else 'rename/copy only'} in_tree={'yes' if p in tree else 'no'}")

    out("\n## (b) token shapes")
    for (name, tok), r in sorted(sc.b.items(), key=lambda kv: (kv[1].variant, kv[0][0])):
        cls, note = cls_of(tok)
        out(f"  [{r.variant}] {name} [{cls}{(': ' + note) if note else ''}] tok {shape(tok)} hits={r.hits} commits={len(r.commits)} {fmt_first(r)} paths={dict(r.paths.most_common(3))} tree={big.count(tok)}")
        if contexts:
            out(f"      ctx: {r.ctx}")

    for label, store in (("(c) password/PSK/secret/token/key-named literals", sc.c), ("(d) SSID literals", sc.d)):
        out(f"\n## {label}: {len(store)} distinct values")
        out(f"  by variant: {dict(Counter(r.variant for r in store.values()))}")
        out(f"  by class: {dict(Counter(cls_of(v)[0] for v in store))}")
        for v, r in sorted(store.items(), key=lambda kv: (kv[1].variant, kv[1].first[0] if kv[1].first else 0)):
            n = big.count(v)
            files = sorted(p for p, t in tree.items() if v in t)[:4] if n and len(v) >= 6 else []
            out(f"  {r.variant} {show(v)} hits={r.hits} commits={len(r.commits)} keys={sorted(r.keys)[:4]} {fmt_first(r)}")
            out(f"      paths={dict(r.paths.most_common(4))} tree={n} {files}")
            if contexts:
                out(f"      ctx: {r.ctx}")

    out("\n## literal trace of withheld values (every added line, blob line and message holding one)")
    for v in sorted(trace_vals, key=lambda x: min(t[0] for t in trace[x]) if trace[x] else 0):
        occ = sorted(trace[v])
        out(f"  {show(v)}: {len(occ)} occurrences in {len({o[1] for o in occ})} commits; tree at {rev}: {big.count(v)}")
        for ct, c, p, ln, ctx in occ[:12]:
            out(f"      {c} {day(ct)} {p}:{ln} | {ctx[:160]}")

    out("\n## (e) high-entropy tokens")
    out(f"  identifier-like (made of words or low class alternation), not counted further: {sc.e_ident}")
    for fam, n in sc.e_fam.most_common():
        out(f"  family {fam}: {n} occurrences, {len(sc.e_fam_distinct[fam])} distinct")
    out(f"  outside a known family: {len(sc.e_resid)} distinct")
    for v, r in sorted(sc.e_resid.items(), key=lambda kv: (kv[1].first[2] if kv[1].first else "")):
        cls, note = CLASSES.get(sha8(v), ("resid", ""))
        segs = "/".join(str(len(x)) for x in re.split(r"[/_+\-]", v))
        out(f"  [{cls}{(': ' + note) if note else ''}] {shape(v)} segs={segs[:40]} hits={r.hits} {fmt_first(r)} tree={big.count(v)}")
        if contexts:
            out(f"      ctx: {r.ctx}")

    out("\n## (f) MAC addresses (OUI only) and private IPv4")
    tree_mac: Counter[str] = Counter()
    tree_mac_files: dict[str, set[str]] = defaultdict(set)
    tree_ip: Counter[str] = Counter()
    tree_ip_files: dict[str, set[str]] = defaultdict(set)
    for p, t in tree.items():
        for rx in (MAC_RE, MAC_H_RE):
            for m in rx.finditer(t):
                o = m.group(1).lower().replace("-", ":")[:8]
                tree_mac[o] += 1
                tree_mac_files[o].add(p)
        for m in IP_RE.finditer(t):
            if private_ip(m.group(1)):
                tree_ip[m.group(1)] += 1
                tree_ip_files[m.group(1)].add(p)
    oui: dict[str, list[Rec]] = defaultdict(list)
    for v, r in sc.mac.items():
        oui[v[:8]].append(r)
    for o, recs in sorted(oui.items()):
        paths: Counter[str] = Counter()
        for r in recs:
            paths.update(r.paths)
        first = min(r.first for r in recs if r.first)
        out(f"  OUI {o} distinct={len(recs)} hits={sum(r.hits for r in recs)} first {first[1]} {day(first[0])} {first[2]}:{first[3]}")
        out(f"      paths={dict(paths.most_common(5))} tree={tree_mac[o]} {sorted(tree_mac_files[o])[:5]}")
    for v, r in sorted(sc.ip.items(), key=lambda kv: [int(x) for x in kv[0].split(".")]):
        out(f"  IP {v} hits={r.hits} {fmt_first(r)} paths={dict(r.paths.most_common(4))} tree={tree_ip[v]} {sorted(tree_ip_files[v])[:4]}")
    out(f"\ntotal runtime {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
