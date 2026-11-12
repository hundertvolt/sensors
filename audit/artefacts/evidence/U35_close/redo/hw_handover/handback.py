"""Rebuilds the single hand-back file: the aggregate over every day's long runs on top, then one section per day with
every run's sanitised output (no LAN addresses, no credential), and the FRAM dump once at the end. Keeps the sections
of earlier days found in the file; usage: python3 handback.py LOGDIR HANDBACK.md DAY (YYYYMMDD)."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate import fold  # noqa: E402

LAN = re.compile(r"^IP=|\b192\.168\.\d+\.\d+|\b10\.\d+\.\d+\.\d+|\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+")
DAY_RE = re.compile(r"<!-- day (\d{8}) -->\n(.*?)<!-- end day -->\n", re.S)
FRAM_RE = re.compile(r"<!-- fram -->\n(.*?)<!-- end fram -->\n", re.S)


def clean(lines: list[str], fram: bool = False) -> list[str]:
    out = []
    for line in lines:
        line = line.rstrip("\r")
        if LAN.search(line) or (not fram and "1234567" + "8" in line):
            continue
        out.append(line)
    return out


def main() -> None:
    logdir, target, day = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    old = target.read_text() if target.exists() else ""
    days = dict(DAY_RE.findall(old))
    fram = FRAM_RE.search(old)
    fram_text = fram.group(1) if fram else ""
    parts = []
    for log in sorted(logdir.glob(f"*_{day}.log")):
        lines = log.read_text(errors="replace").splitlines()
        if log.name.startswith("fram_raw_dump"):
            fram_text = "```\n" + "\n".join(clean(lines, fram=True)) + "\n```\n"
            continue
        if log.name.startswith("build"):
            lines = lines[-30:]
        parts.append(f"### {log.stem}\n\n```\n" + "\n".join(clean(lines)) + "\n```\n")
    days[day] = "\n".join(parts)
    every = [ln for text in days.values() for ln in text.splitlines()]
    short = [ln[4:] for ln in every if ln.startswith("SUM ") and not ln.startswith("SUM L ")]
    body = [
        "# Bench campaign hand-back\n",
        "Rebuilt by `handback.py` after every step; the newest day is complete up to its last finished step.\n",
        "## Aggregate over every day's long runs\n\n```\n" + "\n".join(fold(every)) + "\n```\n",
        "## Short runs (every day)\n\n```\n" + "\n".join(short) + "\n```\n",
    ]
    for d in sorted(days):
        body.append(f"## Day {d}\n\n<!-- day {d} -->\n{days[d].strip()}\n<!-- end day -->\n")
    if fram_text:
        body.append(f"## FRAM raw dump (before the flash)\n\n<!-- fram -->\n{fram_text}<!-- end fram -->\n")
    target.write_text("\n".join(body))


if __name__ == "__main__":
    main()
