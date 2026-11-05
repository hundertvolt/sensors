"""Round 1's bench helper, CPython stdlib only: `handback LOGDIR HANDBACK.md` (the step table on stdin) and `get PATH
WAIT_S [FILE]` (GET /PATH at $DUT_IP as SUM lines; FILE: /status kept verbatim, or /system's image record). Every line
reaching HANDBACK.md passes October's clean() and SECRET; /status's networking section, holding addresses, never does."""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hw_handover"))
from aggregate import fold  # noqa: E402
from handback import clean  # noqa: E402

BUDGET = (9, 126, 14, 422)  # the sheet's round plus the GC proof (3g-5g): FC, FS owned, NVM, prerequisite writes
KNOWN: "tuple[str, ...]" = ()  # standing FAILs by node prefix; none since dev's responder ring holds the 400 ms window
TAIL = {"4a": 200}  # the lower levels' last lines, their summary blocks among them
SECRET = re.compile(r"[\"']PW[\"']\s*:|(?<!_)password[\"']?\s*[:=]", re.I)  # a PW key or a password value; not a test name
SECTION = re.compile(r"<!-- step (\S+) -->\n(.*?)<!-- end step -->\n", re.S)
OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # the board is on the LAN, never behind a proxy


def safe(lines: list[str], fram: bool = False) -> list[str]:
    return [ln for ln in clean(lines, fram) if not SECRET.search(ln)]


def fetch(path: str, wait_s: float) -> "bytes | None":
    ip, end = os.environ.get("DUT_IP", ""), time.monotonic() + wait_s
    while ip:
        try:
            with OPEN.open(f"http://{ip}/{path}", timeout=10) as answer:
                return answer.read()
        except OSError:
            if time.monotonic() >= end:
                break
            time.sleep(5)
    return None


def digest(status: dict) -> list[str]:
    # The system section (ResetReason), the sensors section and each logger's errcount entry, one line each.
    lines = [f"SUM status {key}={json.dumps(status.get(key), sort_keys=True)}" for key in ("system", "sensors")]
    return lines + [f"SUM errcount {k} {json.dumps(v, separators=(',', ':'))}" for k, v in sorted((status.get("errcount") or {}).items())]


def get(path: str, wait_s: str, file: str = "") -> int:
    raw = fetch(path, float(wait_s))
    try:
        body = json.loads(raw) if raw is not None else None
    except ValueError:
        body = None
    if not isinstance(body, dict):
        print(f"SUM {path} not read: {'no JSON answer' if os.environ.get('DUT_IP') else 'DUT_IP unset'}")
        return 1
    if path == "system":  # the board's BuildDate against the build's image record
        board, built = (body.get("build") or {}).get("BuildDate"), json.loads(Path(file).read_text()).get("BuildDate")
        print(f"SUM image board_BuildDate={board} record_BuildDate={built} match={int(board == built)}")
        return int(board != built)
    if file:
        Path(file).write_bytes(raw or b"")  # verbatim and local only: networking holds the board's addresses
    print("\n".join(digest(body) if path == "status" else [f"SUM {path} {json.dumps(body, sort_keys=True)}"]))
    return 0


def failed(run: list[str]) -> list[str]:
    names, inside = [], False
    for ln in run:
        if inside and ln.startswith("  - "):
            names.append(ln[4:].split(": ", 1)[0].replace("tests_hardware/", ""))
        else:
            inside = ln.startswith("Failed:")
    return names


def verdict(lines: list[str]) -> list[str]:
    # [verdict, ResetReason after, started, took, the host's 1-minute load at the end] of the newest run in one step log.
    starts = [i for i, ln in enumerate(lines) if ln.startswith("== step ") and " start " in ln]
    if not starts:
        return ["not run", "", "", "", ""]
    run = lines[starts[-1] :]
    end = next((re.search(r" end rc=(\d+) .* (\d+)s load (\S+)", ln) for ln in run if ln.startswith("== step ") and " end rc=" in ln), None)
    parts = [f"rc={end[1]}" if end else "running or cut off (partial log)"]
    parts += [ln[8:].strip() for ln in run if ln.startswith("Result: ")]
    names = [f"{n} (known)" if any(k in n for k in KNOWN) else n for n in failed(run)]
    if names:
        parts.append("failed: " + ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else ""))
    parts += [ln.strip() for ln in run if re.match(r"NOTE |SUM .*refused", ln)][:2]
    resets = [m[1] for ln in run if ln.startswith("SUM status system=") for m in [re.search(r'"ResetReason": (-?\d+)', ln)] if m]
    took = f"{int(end[2]) // 3600}h{int(end[2]) % 3600 // 60:02d}" if end else ""
    started = " ".join(run[0].split(" start ", 1)[1].split()[:2])
    return ["; ".join(parts), resets[-1] if resets else "", started, took, end[3] if end else ""]


def handback(logdir: Path, target: Path) -> int:
    # Steps whose log is not in LOGDIR (a fresh checkout) keep their row and section from the pushed file.
    old = target.read_text(errors="replace") if target.exists() else ""
    old_rows, old_logs = dict(re.findall(r"^\| (\S+) \| (.*)$", old.split("## Logs", 1)[0], re.M)), dict(SECTION.findall(old))
    table = [ln.split("|") for ln in sys.stdin.read().splitlines() if ln]
    rows, logs, every, spent = [], {}, [], [0, 0, 0, 0]
    for f in table:
        sid, wear = f[0], "/".join(f[3:7])
        path = logdir / f"{sid}.log"
        if path.exists():
            lines = path.read_text(errors="replace").splitlines()
            kept = lines[-TAIL[sid] :] if sid in TAIL else lines
            logs[sid] = "```\n" + "\n".join(c for ln in kept for c in safe([ln], ln.startswith("FRAM "))) + "\n```\n"
            v = verdict(lines)
            row = " | ".join([f[1], *(safe([v[0]]) or ["(verdict filtered: see the log)"]), *v[1:], wear]) + " |"
        else:
            row = old_rows.get(sid, f"{f[1]} | not run |  |  |  |  | {wear} |")
            if sid in old_logs:
                logs[sid] = old_logs[sid]
        rows.append(f"| {sid} | {row}")
        if not row.split(" | ")[1].startswith("not run"):
            spent = [a + int(b) for a, b in zip(spent, f[3:7])]
        every += logs.get(sid, "").splitlines()
    head = [
        "# Round 1 bench hand-back\n",
        f"Rebuilt by `round1.py` after every step, last {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC. Each verdict "
        "is its step's newest run; after step 4a a passing pytest step reads NOT CLEAN (lower levels skipped).\n",
        "| step | name | verdict | ResetReason after | started (UTC) | took | host load at end | FC/FS/NVM/pre |",
        "|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        "Wear started (the sheet's maxima per started step): "
        + ", ".join(f"{k} {v} of {b}" for k, v, b in zip(("FC", "FS owned", "NVM", "prerequisite writes"), spent, BUDGET))
        + ".\n",
        "## Long runs summed (October's aggregate)\n\n```\n" + "\n".join(fold(every)) + "\n```\n",
        "## Logs\n",
    ]
    runner = logdir / "runner.log"
    if runner.exists():
        head.append("### runner\n\n```\n" + "\n".join(safe(runner.read_text().splitlines())) + "\n```\n")
    order = [f[0] for f in table]
    names = {f[0]: f[1] for f in table}
    head += [f"### {s} {names[s]}\n\n<!-- step {s} -->\n{logs[s]}<!-- end step -->\n" for s in order[1:] + order[:1] if s in logs]
    target.write_text("\n".join(head))
    return 0


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    sys.exit(handback(Path(args[0]), Path(args[1])) if cmd == "handback" else get(*args))
