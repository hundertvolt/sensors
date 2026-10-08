"""Tag harvest items whose source text left the tree between two baselines with what became of it.

Usage: baseline_fates.py OLD NEW. Appends one `⟨NEW: fate⟩` tag per affected item in audit/harvest/*.md
(idempotent). Fates of the retired queue/handover rows are the table below, read from the commits
2a88cc8..4dc80ef and from where BACKLOG.md's "Real-hardware work still owed" now holds each row.
"""

import glob
import re
import subprocess
import sys

from harvest_check import items
from harvest_merge import wrap

Q, H = "REAL_HARDWARE_TEST_QUEUE.md", "HARDWARE_TEST_HANDOVER.md"
OWED = "open in BACKLOG.md \"Real-hardware work still owed\""
ROW = {
    "D1": f"standing answer, {OWED} (\"How a sitting runs\")", "D2": f"standing answer, {OWED} (\"How a sitting runs\")",
    "D3": f"standing answer, {OWED} (\"How a sitting runs\")",
    "S3b": f"{OWED} (M1 + S3b)", "M1": f"{OWED} (M1 + S3b)",
    "S4": "open: BACKLOG.md \"Real-hardware re-test of the segfault fix\" (the 6 h soak)",
    "T1": f"measured 2026-09-25, owner to close: {OWED} (T1)", "T2": "done 2026-09-25, row retired (6e40e27)",
    "T4": f"measured 2026-09-25, owner decisions open: {OWED} (T4, holds A6's script)",
    "A6": f"script kept only in {OWED} (T4)",
    "G1": "scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df; BACKLOG.md:92-94)",
    "G4": "scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df; BACKLOG.md:92-94)",
    "G3": "done 2026-09-25: reboot_fallback_starves_the_watchdog.py + test_watchdog_starvation.py, 3/3 (79423dd)",
    "G6": "decided (adapt now, measure later): BACKLOG.md item 12 and \"Still owed elsewhere\"",
    "G8": "retired 2026-09-25: covered by test_serving_sweep_at_the_reactive_default (2f48f86)",
    "G10": "excluded on purpose (arduino/ out of scope): BACKLOG.md \"Still owed elsewhere\"",
    "G12": "done 2026-09-25: uart_driver_read_never_blocks_the_loop.py, 7/7 (2f48f86)",
    "N2": "verified on silicon 2026-09-25, row retired (6f7eef7); SPECIFICATION.md L records it",
    "N3": f"needs a babbling peer the bench lacks: {OWED} (R13 + N3)",
    "R13": f"needs a babbling peer the bench lacks: {OWED} (R13 + N3)",
    "R1": "closed 2026-09-25: BACKLOG 30 not reproduced (18/18 clean), item and row retired (79423dd)",
    "R2": "measured 2026-09-25: BACKLOG.md items 24 and 32",
    "R4": "done 2026-09-25 (zero-wear, 14.58 s at three readers), row retired (6e40e27)",
    "R5": "closed 2026-09-25 (third BMP3XX pass), row and BACKLOG entry retired (6e40e27)",
    "R6": "measured 2026-09-25: +0.90 s did not reproduce (~53 ms); retired into SPECIFICATION.md A.7 (38b270d)",
    "R7": "measured 2026-09-25 on silicon, retired into SPECIFICATION.md A.7 (38b270d)",
    "R9": "shadow half confirmed on silicon; Overrange half rides S3b (BACKLOG.md ISL29125 open question)",
    "F1": "verified 2026-09-25, row retired (6f7eef7); two loose ends are a BACKLOG.md deferred entry",
    "F17": "open: BACKLOG.md item 44", "F18": f"owner decision open: {OWED} (F18)",
    "H1": "open: BACKLOG.md chroot entry (\"Still owed elsewhere\")",
    "W3": f"measured like for like 2026-09-25 (+17 %), owner judgement: {OWED} (W3)",
    "W4": "done clean 2026-09-24/25, row retired (851e816)",
    "W5": "done 2026-09-25, SPECIFICATION.md I.3 corrected to the measured case (6e40e27)",
}
QUOTE = {  # items whose quoted text was reworded or removed upstream, 2a88cc8..4dc80ef
    "CORE.N236": "R5 closed 2026-09-25, this BACKLOG entry retired (6e40e27); the residual window stays in SPECIFICATION.md:3638-3660",
    "CORE.N237": "BACKLOG entry retired with R5 (6e40e27); the residual window stays in SPECIFICATION.md:3638-3660",
    "HW.N769": "BACKLOG entry retired with R5 (6e40e27)",
    "DOC.N192": "drift resolved: the reference now reads \"F11, HEAP_FRAGMENTATION_MEASUREMENTS.md archive\" (03f8bcf)",
    "DOC.N282": "drift resolved: BACKLOG.md:10-11 now points at its own \"Real-hardware work still owed\" (03f8bcf)",
    "DOC.N286": "drift resolved: the shadow fix is recorded as confirmed on silicon; only Overrange owes a run (03f8bcf)",
    "DOC.N287": "drift resolved: item 12 now names G6 (03f8bcf)",
    "DOC.N290": "drift resolved: the R10 reference is gone (03f8bcf)",
    "HW.N277": "reference repointed to \"BACKLOG.md (G6)\" (03f8bcf); the test still fails by construction until G6's method exists",
    "HW.N768": "README's queue entry removed with the file (03f8bcf)",
    "HW.N770": "reworded: \"Settled: ... a structural exception until injection hardware exists (2026-09-22, Part E.6.6's fourth item)\" (BACKLOG.md:90-92)",
    "HW.N773": "BACKLOG 30 closed as not reproduced, item removed (R1, 79423dd)",
    "REST.N171": "BACKLOG 30 closed as not reproduced, item removed (R1, 79423dd)",
    "REST.N172": "BACKLOG 30 closed as not reproduced, item removed (R1, 79423dd)",
    "HW.N776": "F1 verified 2026-09-25 (6f7eef7); the script still needs a watchdog-feeding wrapper: BACKLOG.md \"Two device-script loose ends\" and tests_hardware/README.md:383-385",
    "LED.N063": "G4 scratched by the owner 2026-09-25: src/ is never changed only for a test (230a8df)",
    "STOR.N137": "G4 scratched by the owner 2026-09-25 (230a8df); tests_hardware/README.md:1287-1292 now says so",
    "UART.N225": "G1 scratched by the owner 2026-09-25 (230a8df); tests_hardware/README.md:1265-1269 now says so",
    "PERF.N028": "R6 re-measured 2026-09-25: the +0.90 s did not reproduce (~53 ms); SPECIFICATION.md A.7 rewritten (38b270d)",
    "SENS.N379": "reworded: the shadow fix is confirmed on silicon, only the Overrange half owes a run (03f8bcf)",
}
SECTION = ("section retired with the file (03f8bcf): open rows moved to BACKLOG.md \"Real-hardware work "
           "still owed\"; the traps live in tests_hardware/README.md, CLAUDE.md and SPECIFICATION.md")


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=False).stdout


def row_at(lines, n):
    for i in range(min(n, len(lines)) - 1, -1, -1):
        m = re.match(r"^\s*(?:[-|]\s*)?(?:\[[ x~]\]\s*)?\**([A-Z]{1,2}\d{1,2}[a-z]?)\**\b", lines[i])
        if m and m[1] in ROW:
            return m[1]
        if lines[i].startswith("#"):
            return None
    return None


def fate(text, old_files):
    rows = set()
    for f, lines in old_files.items():
        for m in re.finditer(re.escape(f) + r":(\d+)", text):
            r = row_at(lines, int(m[1]))
            if r:
                rows.add(r)
    rows |= {r for r in re.findall(r"\b([A-Z]{1,2}\d{1,2}[a-z]?)\b", text) if r in ROW}
    if rows:
        return "; ".join(f"{r} {ROW[r]}" for r in sorted(rows))
    return SECTION


if __name__ == "__main__":
    old, new = sys.argv[1], sys.argv[2]
    old_files = {f: git("show", f"{old}:{f}").split("\n") for f in (Q, H)}
    tag = f"⟨{new}:"
    done = 0
    for p in sorted(glob.glob("audit/harvest/*.md")):
        text = open(p, encoding="utf-8").read()
        for it in items([p]):
            if tag in it["text"]:
                continue
            gone = Q in it["text"] or H in it["text"]
            if not gone and it["id"] not in QUOTE:
                continue
            note = QUOTE.get(it["id"]) or (fate(it["text"], old_files) if gone else None)
            if note is None:
                print("no fate for", it["id"])
                continue
            lines = text.split("\n")
            i = next(k for k, ln in enumerate(lines) if ln.startswith(f"- **{it['id']}** "))
            while i + 1 < len(lines) and lines[i + 1].startswith("  "):
                i += 1
            lines[i + 1:i + 1] = wrap(f"{tag} {note}⟩", "  ", "  ")
            text = "\n".join(lines)
            done += 1
        open(p, "w", encoding="utf-8").write(text)
    print(f"tagged {done} items")
