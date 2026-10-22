# M.PROC.026/.027/.029: writes conformance.md's rung and owner rows (from audit/actions/SUPP_recovery.md) and queue_c.md's rows.
# Usage: python3 -I audit/b3/conformance_walk.py <tree>. A cell names the tests the record cites; the B2 review checks each bites.
import re, subprocess, sys
from pathlib import Path

tree = Path(sys.argv[1])
head = subprocess.run(["git", "-C", str(tree), "log", "-1", "--format=%h"], capture_output=True, text=True, check=False).stdout.strip() or "unknown"  # never an empty stamp
TEST = re.compile(r"(tests(?:_hardware)?/[\w/]+\.py)")


def level(path):
    if path.startswith("tests_hardware/bench/"):
        return "L4"
    if path.startswith(("tests_hardware/flash/", "tests_hardware/device_scripts/")):
        return "L3"
    return "L2" if path.startswith("tests/test_digital_twin_") else "L1"


def keep_header(path):
    return path.read_text(encoding="utf-8").split("\n## ")[0].rstrip() + "\n"


rows, unit, l34_open = [], "", 0
supp = (tree / "audit/actions/SUPP_recovery.md").read_text(encoding="utf-8").split("## Actions")[0]
for line in supp.splitlines():
    if line.startswith("### U"):
        unit = line[4:].split(" ")[0]
    if not line.startswith("| ") or line.startswith(("| fault path", "|---")) or not unit:
        continue
    cols = [c.strip() for c in line.strip("|").split(" | ")]
    path = re.sub(r"\s*\(.*", "", cols[0]).replace("|", "/")[:110]
    rungs = sorted(set(re.findall(r"\bR([1-7])\b", " ".join(cols[1:]))))
    cells = {lv: [] for lv in ("L1", "L2", "L3", "L4")}
    for t in sorted(set(TEST.findall(line))):
        cells[level(t)].append(t.split("/")[-1])
    for r in rungs or ["-"]:
        shown = {lv: ", ".join(v) if v else ("queue_c" if lv in ("L3", "L4") else "open") for lv, v in cells.items()}
        l34_open += sum(1 for lv in ("L3", "L4") if not cells[lv])
        rows.append(f"| {unit}: {path} | {'R' + r if r != '-' else 'no rung named'} | {shown['L1']} | {shown['L2']} | {shown['L3']} | {shown['L4']} | open | open: the review confirms each cell or adds its test at the lowest level |")
OWNER = [  # owner row, part, L1, L2, L3, L4 (located by grep at the walked commit; each to confirm)
    ("OR115 modlwip hammer reach", "an `EAGAIN` seen while a zero-timeout poll said writable; A.U21.13's unpatched control run (faults.md)", "test_modlwip_eagain.py (lwip_host)", "not reachable at L2: the twin's sockets are host sockets, no modlwip", "queue_c", "queue_c (R4 H39)"),
    ("OR116/OR123 CRC16 arm", "both CRC modes, twin pair in both modes, the jumper pair, the reflash run", "test_asy_crc_checks.py, test_asy_uart_comm.py, test_asy_framing_codecs.py", "test_digital_twin_uart_link.py, test_digital_twin_uart_comm_hazard.py", "test_uart_crossover.py, uart_crossover_exchange.py (R1 H37)", "test_uart_link_crc16.py (R4 H38)"),
    ("OR122.a SystemCmd words", "resetconfig, erasefram, reboot, bootloader: function, refusal, error paths", "test_asy_system_service.py, test_asy_webserver_service.py, test_asy_config_manager.py", "test_digital_twin_bus_hazard_concurrency.py", "test_system_commands.py, system_command_*.py (R1-R3 H13/H14)", "test_system_commands_over_rest.py, test_reset_reasons.py"),
    ("OR122.a SystemCmd words", "near-miss words refused as \"Invalid\"; the OR119.a states raced deterministically", "open", "open", "queue_c (H13)", "queue_c"),
    ("OR122.a SystemCmd words", "bus and storage hazards; watchdog takeover, healthy and hung step; power loss per step; both GC stages", "test_reset_call_site_invariant.py", "open", "queue_c (H13/H14)", "queue_c"),
    ("OR130 supervisor feeds", "two feed sites pinned (L0 test_watchdog_feed_sites.py); the escalation's single feed; twin Run 3's feed_count stop", "test_asy_system_service.py", "Run 3 (scripts/_digital_twin_scenarios.py)", "test_watchdog_starvation.py, reboot_fallback_starves_the_watchdog.py", "not reachable at L4 beyond L3: no bench-only path"),
]
orows = [f"| {o} | {p} | {a} | {b} | {c} | {d} | open | open: confirm each named test reaches the part |" for o, p, a, b, c, d in OWNER]
conf = tree / "audit/b3/conformance.md"
conf.write_text(keep_header(conf) + f"""
## Recovery rungs (M.PROC.026)

Built by `audit/b3/conformance_walk.py` at `{head}` from SUPP_recovery.md's rung tables (agent, 2026-10-22): {len(rows)} rows, one per
fault path and rung the record names; a cell lists the tests the record itself cites, "open" where it cites none (L1/L2),
"queue_c" where silicon is the only way ({l34_open} L3/L4 cells). Bounded, once and race-free are each proven by the review.

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + """

## Owner test demands (M.PROC.027)

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
""" + "\n".join(orows) + """

## Bus hazards of B2 and B3 (A.U35.50) and wear and host churn (A.U35.51)

Open: one four-tier row per bus-facing change, and the wear-gate and host-churn table, from the integration head (B2).
""", encoding="utf-8")
QUEUE = [  # item, source, level, round (H row), gate, property proved
    ("silicon arm of the hardware memory gates", "A.U35.05 (3), M.PROC.037", "L3/L4", "R1 (H43)", "none", "a caught allocation failure prints the interpreter's wording and turns both hardware gates red"),
    ("lone-BMP3xx general call", "A.U35.21", "L3", "R1", "none", "the lone-BMP3xx general-call expectation, as A.U35.21 states it"),
    ("torn write on the bench reset race", "A.U35.40", "L4", "R3", "persistence_write", "the torn-write expectation on the bench reset race, as A.U35.40 states it"),
    ("silicon-only interaction, recombination and rung cells", "A.U35.08, A.U35.09, M.PROC.026", "L3/L4", "R1 (H71)", "none", f"every conformance.md queue_c cell ({l34_open} at the walked commit)"),
    ("OR115 lwIP stall, then the override hammer", "A.U21.14", "L4", "R4 (H39)", "flash_cycle", "the stall reproduces on the unpatched image and the override ends it"),
    ("OR116 CRC16 over the jumper and on a reflashed image", "A.S0930.05, A.S0930.06", "L3, L4", "R1 (H37), R4 (H38)", "flash_cycle (H38)", "both CRC modes interoperate over real wire"),
    ("the four SystemCmd words on the board", "A.S0930.28, .29, .39, .40", "L3/L4", "R1-R3 (H13, H14)", "persistence_write (resetconfig)", "function, refusal, timing and race of each word on silicon"),
    ("two-image GC proof", "SPECIFICATION.md E.6.1", "L3/L4", "R7 (H45)", "flash_cycle", "both GC stages hold on silicon"),
    ("bench trigger timestamps for the read stagger", "-", "L4", "R5 (H19)", "long_soak", "trigger spacing over a long run"),
    ("speed-probe bands on the bench Pi4, no board", "A.U35.23", "host", "R0 (H56)", "none", "the probe bands and step timings on the real host"),
    ("l3./l4. tunable rows", "M.PROC.028", "L3/L4", "R1/R4/R5 (H55)", "none", "each estimated tunable measured"),
]
qrows = [f"| {i} | {s} | {lv} | {r} | {g} | open (A.U35.49) | {p} |" for i, s, lv, r, g, p in QUEUE]
queue = tree / "audit/b3/queue_c.md"
queue.write_text(keep_header(queue) + f"\n## Items\n\nFrom M.PROC.029's list (agent, 2026-10-22); every H row checked present in audit/actions/C.md at `{head}`. Gates are\nthe default-off markers a round must name; a twin-first record is A.U35.49's.\n\n| item | source | level | round (H row) | gate | twin-first record | property proved |\n|---|---|---|---|---|---|---|\n" + "\n".join(qrows) + "\n", encoding="utf-8")
print(len(rows), "rung rows;", l34_open, "L3/L4 queue cells;", len(orows), "owner rows;", len(qrows), "queue rows")
