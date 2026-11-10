#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""The few lines of a long log that decide its run: each runner summary block (SPECIFICATION.md E.10) with its skip
and deselect lists folded to counts, plus the decisive lines a 25,000-line log buries (.claude/skills/work-routines)."""

# Usage: _log_verdict.py [--all] PATH [PATH ...]; "-" reads standard input (a bench log: git show REF:PATH | ...). A named
# file is always shown, a directory's *.log, *.out and *.txt only when notable. Exit 0 / 1 notable / 2 on usage.

import re
import sys
from pathlib import Path

# The repo root is appended, so the twin gate's own values resolve: never a copy of them.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts._twin_process import FEED_GAP_SHARE_MAX, MEMORY_ERROR_MARKERS

_LIST_CAP = 12  # a block's listed items shown before "+N more"
_HIT_CAP = 5  # failure and marker lines shown per file
_WIDTH = 240  # a shown line's longest form
_FOLDED = ("Skipped", "Deselected")
_FINDINGS = ("Failed", "Passed only on retry", "Recovery passes", "Checked nothing")
_SUFFIXES = (".log", ".out", ".txt")
_SHUTDOWN = re.compile(r"would_have_triggered_count=(\d+).*largest_feed_gap_ms=(\d+).*wdt_timeout_ms=(\d+)")
_ONE_LINER = re.compile(r"== Test parallelism: |== Image: |Success: no issues found|Found \d+ errors? in \d+ file|All checks passed!|^\d+/\d+ tests collected")
_PYTEST_TOTAL = re.compile(r"^=*\s*\d+ (passed|failed|errors?|skipped|deselected)\b.* in \d")
_PYTEST_ITEM = re.compile(r"^(FAILED|ERROR) ")
_MICROTEST = re.compile(r"\d+/\d+ passed, (\d+) failed")
_FAILED_TEST = re.compile(r"\b(FAIL|ABORT) test_")
_EXCEPTION = re.compile(r"\b\w*(Error|Exception|Interrupt)\b:?")
# A board console's error lines, counted where a log has no summary block; an unhandled one is a finding.
_CONSOLE = ("Unhandled exception", "Traceback (most recent call last)", "UART error", "Resync")
# A marker in quotes is a gate or a test naming what it looks for, never the interpreter's own message.
_MARKER = re.compile("|".join(rf"(?<![\'\"]){re.escape(marker)}" for marker in MEMORY_ERROR_MARKERS))


def _blocks(lines: list[str]) -> list[list[str]]:
    # Every summary block, its lines stripped of the job tag they were printed under ("[scenarios[dev]] "); parallel
    # jobs interleave theirs, and another tier's progress dots can land in front of a tag.
    open_blocks: dict[str, list[str]] = {}
    done: list[list[str]] = []
    for line in lines:
        at = line.find("== Summary: ")
        if at >= 0:
            lead = line[:at]
            open_blocks[lead[lead.find("[") :] if "[" in lead else ""] = [line[at:]]
            continue
        tags = [t for t in open_blocks if t in line]
        if not tags:
            continue
        tag = max(tags, key=len)
        content = line[line.find(tag) + len(tag) :] if tag else line
        open_blocks[tag].append(content)
        if content.startswith("Exit code:"):
            done.append(open_blocks.pop(tag))
    return done + list(open_blocks.values())


def _condense(block: list[str]) -> list[str]:
    # A clean pass as one line; any other block with empty sections dropped (but "Failed: none"), folded lists
    # counted and long lists cut.
    heads = {line.partition(":")[0]: line.partition(": ")[2] for line in block if not line.startswith("  - ")}
    if heads.get("Result") == "PASS" and not any(_flagged(block)) and heads.get("Notes", "none") == "none":
        counts = "; ".join(_counts(line) for line in block if line.startswith("Counts ("))
        where = " | ".join(heads[k] for k in ("Levels", "GC stage") if k in heads)
        return [f"PASS {block[0].removeprefix('== Summary: ').removesuffix(' ==')} | {where} | {counts}"]
    out: list[str] = []
    title, listed = "", 0
    for line in block:
        if line.startswith("  - "):
            listed += 1
            if title in _FOLDED:
                out[-1] = f"{title}: {listed} (listed in the log)"
            elif listed <= _LIST_CAP:
                out.append(_cut(line))
            elif listed == _LIST_CAP + 1:
                out.append("  ... more in the log")
            continue
        title, listed = line.partition(":")[0], 0
        if not line.endswith(": none") or title == "Failed":
            out.append(_cut(line))
    return out


def _counts(line: str) -> str:
    # "Counts (files): passed 137 · failed 0 · skipped 80 ..." as "files: passed 137, skipped 80", zero fields dropped.
    unit, _, fields = line.removeprefix("Counts (").partition("): ")
    kept = [f for f in fields.split(" · ") if not f.endswith(" 0")]
    return f"{unit}: {', '.join(kept) or 'nothing counted'}"


def _cut(line: str) -> str:
    # One shown line: unprintable characters as "?", a long one cut with a visible mark.
    line = "".join(c if c.isprintable() and c != "\ufffd" else "?" for c in line)
    return line if len(line) <= _WIDTH else line[: _WIDTH - 1] + "\u2026"


def _extras(lines: list[str], *, blocks: bool) -> tuple[list[str], bool]:
    # The decisive lines outside the blocks (a test file's closing line too, in a log with no block), and whether any of
    # them is notable.
    out: list[str] = []
    seen: set[str] = set()
    notable = False
    for line in lines:
        hit = _ONE_LINER.search(line)
        if hit and line not in seen:
            seen.add(line)
            out.append(_cut(line[hit.start() :]))
            notable |= line[hit.start() :].startswith("Found ")
    totals = [line for line in lines if _PYTEST_TOTAL.search(line)]
    if totals:
        out.append("pytest: " + totals[-1].strip("= "))
        notable |= bool(re.search(r"\d+ (failed|errors?)\b", totals[-1]))
    items = [line for line in lines if _PYTEST_ITEM.match(line)]
    out.extend(_cut(line) for line in items[:_HIT_CAP])
    if len(items) > _HIT_CAP:
        out.append(f"  ... {len(items) - _HIT_CAP} more FAILED/ERROR line(s) in the log")
    closing = [line for line in lines if _MICROTEST.search(line)]
    failing = [line for line in closing if (m := _MICROTEST.search(line)) and m.group(1) != "0"]
    out.extend(_cut(line) for line in (failing if blocks else closing)[:_HIT_CAP])
    notable |= bool(failing)
    if not blocks:
        for kind in _CONSOLE:
            numbers = [n for n, line in enumerate(lines, 1) if kind in line]
            if numbers:
                out.append(f"console: {len(numbers)} '{kind}' line(s), first at line {numbers[0]}")
                notable |= kind == "Unhandled exception"
        hits = [(n, m.start(), line) for n, line in enumerate(lines, 1) if (m := _FAILED_TEST.search(line))]
        for n, at, line in hits[:_HIT_CAP]:
            cause = next((later.strip() for later in lines[n : n + 15] if _EXCEPTION.search(later)), "")
            out.append(_cut(f"  line {n}: {line[at:].strip()} {cause}"))
    marks = [(n, line) for n, line in enumerate(lines, 1) if _MARKER.search(line)]
    quoted = sum(1 for line in lines if any(marker in line for marker in MEMORY_ERROR_MARKERS)) - len(marks)
    if marks:
        out.append(f"memory markers: {len(marks)} line(s); check none is a test's own fixture text")
        out.extend(f"  line {n}: {_cut(line.strip())}" for n, line in marks[:_HIT_CAP])
        notable = True
    if quoted:
        out.append(f"memory markers: {quoted} quoted mention(s) skipped (a gate naming what it looks for)")
    gaps = [(n, *map(int, m.groups())) for n, line in enumerate(lines, 1) if (m := _SHUTDOWN.search(line))]
    if gaps:
        # A run whose watchdog would have fired starves it on purpose or fails its own harness check; a near miss is a
        # gap past the share in a run whose watchdog never fired.
        calm = [g for g in gaps if not g[1]]
        near = [g for g in calm if g[2] > FEED_GAP_SHARE_MAX * g[3]]
        worst = max(calm, key=lambda g: g[2] / g[3]) if calm else None
        largest = f"largest feed gap {worst[2]} of {worst[3]} ms ({worst[2] / worst[3]:.0%}) where the watchdog never fired" if worst else "every run's watchdog would have fired"
        out.append(f"twin shutdown lines: {len(gaps)}; {largest}; above {FEED_GAP_SHARE_MAX:.0%}: {len(near)}; watchdog would have fired: {len(gaps) - len(calm)}")
        out.extend(f"  line {n}: feed gap {gap} of {timeout} ms" for n, _fired, gap, timeout in near[:_HIT_CAP])
        notable |= bool(near)
    return out, notable


def _flagged(block: list[str]) -> list[str]:
    # The sections that make even a passing block a finding: a failure, a pass that needed a retry or a recovery, a
    # check that checked nothing.
    return [line for line in block if line.partition(":")[0] in _FINDINGS and not line.endswith(": none")]


def read(path: Path) -> tuple[list[str], bool]:
    # One file's verdict lines and whether it is notable.
    return verdict(path.read_text(errors="replace", encoding="utf-8"))


def verdict(text: str) -> tuple[list[str], bool]:
    # One log's verdict lines and whether it is notable.
    if text.count("\ufffd") * 20 > len(text):
        return ["not a UTF-8 text log: no verdict"], True
    lines = text.splitlines()
    if not lines:
        return ["empty log: no verdict"], True
    # A block that needs reading comes first and a clean pass last, so a capped reader still sees the failures.
    out: list[str] = []
    passes: list[str] = []
    notable = False
    blocks = _blocks(lines)
    for block in blocks:
        shown = _condense(block)
        if not any(line.startswith("Exit code:") for line in block):
            shown.append("(block cut off: the run ended before its Result and Exit code lines)")
        (passes if len(shown) == 1 and shown[0].startswith("PASS ") else out).extend(shown)
        notable |= "Result: PASS" not in block or any(_flagged(block))
    extras, extra_notable = _extras(lines, blocks=bool(blocks))
    out.extend(extras)
    out.extend(passes)
    if not out:
        tracebacks = sum(1 for line in lines if line.startswith("Traceback"))
        out.append(f"no summary block; {tracebacks} traceback(s); last lines:")
        out.extend("  " + _cut(line) for line in lines[-5:])
        notable = notable or tracebacks > 0
    return out, notable or extra_notable


def main(argv: list[str]) -> int:
    if argv[:1] in (["-h"], ["--help"]):
        sys.stdout.write("usage: _log_verdict.py [--all] PATH [PATH ...]\n")
        return 0
    show_all = "--all" in argv
    if "-" in argv:
        out, notable = verdict(sys.stdin.read())
        sys.stdout.write("== <stdin>" + (" [NOTABLE]" if notable else "") + "\n" + "\n".join(out) + "\n")
        return 1 if notable else 0
    paths = [Path(arg) for arg in argv if arg != "--all"]
    try:
        missing = not paths or any(not p.exists() for p in paths)
    except OSError:
        missing = True
    if missing:
        sys.stderr.write("usage: _log_verdict.py [--all] PATH [PATH ...] (each an existing file or directory)\n")
        return 2
    files = [(f, p.is_file()) for p in paths for f in ([p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file() and q.suffix in _SUFFIXES))]
    shown = flagged = 0
    for f, named in files:
        out, notable = read(f)
        flagged += notable
        if notable or show_all or named:
            shown += 1
            sys.stdout.write(f"== {f}{' [NOTABLE]' if notable else ''}\n" + "\n".join(out) + "\n")
    if len(files) > 1 or any(p.is_dir() for p in paths):
        sys.stdout.write(f"== {len(files)} file(s) read, {flagged} notable, {shown} shown\n")
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
