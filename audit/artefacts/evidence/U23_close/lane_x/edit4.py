"""Lane X resume edits: S final, round 2, OF-111, OF-129, A.9 (exact replacements, each found exactly once)."""
import sys
from pathlib import Path

SPEC = Path(sys.argv[1])
text = SPEC.read_text(encoding="utf-8")
EDITS = []


def edit(old: str, new: str) -> None:
    EDITS.append((old, new))


# OF-111: A.8 PUT /status refuses ResetErrors from a shutdown command's acceptance.
edit(
    """  webserver's own history (errno 14, `CALLBACK`: `"Error log reset failed: <name> <exception>"`);
  any other value, and every other key, answers `"Invalid"`; a body without the key resets nothing.
  `/notification` — settings + `LightCmdLED`""",
    """  webserver's own history (errno 14, `CALLBACK`: `"Error log reset failed: <name> <exception>"`);
  any other value, and every other key, answers `"Invalid"`; a body without the key resets nothing.
  From the acceptance of a `reboot`, `bootloader`, `resetconfig` or `erasefram` command until the
  unit restarts, `ResetErrors` answers `"Failed"` and clears nothing, so the logs survive into the
  reset (owner, 2026-10-13, asked "refuse `ResetErrors` once a reboot or erase command has been
  accepted?", option (b) reading "Refuse it ("Failed") from the command's acceptance on: ... the logs
  survive into the reboot.": "1 b").
  `/notification` — settings + `LightCmdLED`""",
)
edit(
    """a sequence is accepted, before any chip or flash write; `mempause` is refused too, and `ResetErrors`
answers "Failed" once the sequence has closed FRAM. The unit tier proves it on every generated""",
    """a sequence is accepted, before any chip or flash write; `mempause` is refused too, and `ResetErrors`
answers "Failed" from the moment a sequence is accepted, clearing nothing, so the FRAM-backed logs
survive into the reset. The unit tier proves it on every generated""",
)

# A.9: the staged example paths (stale since before this unit; the stage holds the page and the bundle).
edit(
    """(`<staged>/index.html`, `<staged>/definitions/wozi.json`, `<staged>/js/render.js`) and a shared dir""",
    """(`<staged>/index.html`, `<staged>/js/app.js`) and a shared dir""",
)

# OF-129: C.7, a hotspot window that cannot be armed is a hardware failure too.
edit(
    """does, and the streak climbs the same way while task restarts keep the silent mode (agent,
2026-10-12).""",
    """does, and the streak climbs the same way while task restarts keep the silent mode (agent,
2026-10-12). A hotspot window that cannot be armed is a hardware failure too: with no window the
hotspot never ends and STA is never retried, so each failed arm counts, the streak climbs to the
device rung and the give-up, and the task's restart leaves the hotspot for a fresh STA streak with
the hotspot available once more; repeated task ends charge the supervisor's budget, which reboots
(owner, 2026-10-13, asked "should a failed hotspot-window timer count as a hardware failure?",
option (b) reading "Count it like the silent mode does: it feeds the streak, then the task restart,
then the budget's reboot.": "Take option b for 2", after their follow-up "this means that currently
the window timer continously fails, the Hotspot never ends, and option b makes it try to restart
the task and if unsuccessful reboots, like normal modules do?" was answered yes).""",
)

# OF-129: C.9, a failed hotspot-timer arm counts in both modes.
edit(
    """loop's next iteration; a failed hotspot-timer arm persists `TIMER` and is retried on the next cycle,
and in the silent mode, where it leaves no attempt due, it also counts toward the WiFi task's
hardware streak (C.7).""",
    """loop's next iteration; a failed hotspot-timer arm persists `TIMER`, is retried on the next cycle
and counts toward the WiFi task's hardware streak (C.7): in the silent mode it leaves no attempt
due, in the hotspot mode no end to the window.""",
)

# OF-129: A.4's Wi-Fi state machine, one sentence on the hotspot window.
edit(
    """  will try to connect to the actual wifi settings without a reboot required.'). A second failed STA""",
    """  will try to connect to the actual wifi settings without a reboot required.'). A window whose timer
  cannot be armed counts as a WLAN hardware failure each iteration, so the task gives up and its
  restart leaves the hotspot for a fresh STA streak (owner, 2026-10-13; C.7). A second failed STA""",
)

# X34 (S3 part): H.2's field-format.js reason and the live tier's display oracle.
edit(
    """mirrored from `src/`, G.2, imported by the mock and the production modules), `field-format.js` (pure
formatting, split so Node-context tests can reuse it without DOM types, H.8.1), `render.js`
(controller, delegates DOM to `templates.js`),""",
    """mirrored from `src/`, G.2, imported by the mock and the production modules), `field-format.js` (pure
formatting, no DOM dependency), `render.js` (controller, delegates DOM to `templates.js`),""",
)
edit(
    """answering the six REST paths, A.8, from data composed out of `mockdata/samples.json`).
""",
    """answering the six REST paths, A.8, from data composed out of `mockdata/samples.json`).
`tests_js/_expected_display.js` is the expected-display helper the Node-context and browser tests
share (H.7, H.8.1).
""",
)

# Round 2: H.3's request signature.
edit(
    """`js/poll-manager.js` exports `pollManager.request(url, init, timeoutMs, signal)` and""",
    """`js/poll-manager.js` exports `pollManager.request(url, init, timeoutMs, signal, queueSignal)` and""",
)

# Round 2: H.4 Poll coordination, the switch hand-over.
edit(
    """goes through the one queue (`pollManager.request(url, init, timeoutMs, signal)`), and its shared `AbortController` timeout covers the whole request, the body read included — `DEFAULT_TIMEOUT_MS = 15000`, see the row below for why that exact value. A section that is left aborts its queued and in-flight GETs, and polling pauses while the tab is hidden.""",
    """goes through the one queue (`pollManager.request(url, init, timeoutMs, signal, queueSignal)`), and its shared `AbortController` timeout covers the whole request, the body read included — `DEFAULT_TIMEOUT_MS = 15000`, see the row below for why that exact value. A section that is left drops its queued GETs; its GET on the wire runs to its end, discarded, when the next section is rendered (a switch), and is aborted when the page itself stops (before a reload), with any GET a switch handed it (agent, 2026-10-13, decided on the owner's behalf for review): an aborted GET resets a connection the device is still answering, which the device logs as a peer reset (`wrnno` 48), so ordinary navigation logged one. The cost: the next section's first GET waits for the left one, measured on the twin (2026-10-13) at a median 216.6 ms after the click against 6.6 ms when it was aborted, at most the 15 s request cap. Polling pauses while the tab is hidden.""",
)

# H.4 PUT/GET row: the confirmation texts the render and live tests cite here.
edit(
    """then asks the confirmations (A.8); a declined or suppressed confirmation sends nothing""",
    """then asks the confirmations, an enum's chosen option label or a toggle's card submit label with "?" (A.8); a declined or suppressed confirmation sends nothing""",
)

# X37, round 2: H.7's live tier.
edit(
    """`live-backend-put-matrix.test.js` extends this to every writable field of every device's generated
definitions, a field whose definition an earlier device already covered running once.
""",
    """`live-backend-put-matrix.test.js` extends this to every writable field of every device's generated
definitions, a field whose definition an earlier device already covered running once.

**What the live tier checks.** The smoke applies a `DebugLevel` other than the twin's, then the same
value, expecting exactly "valid", then "unchanged". `runLiveBackendConcurrentTabs` opens the
device's whole `max_connections` of tabs against one twin, all navigating at once: each loads
within the page's request cap plus 5 s or on one reload of its own, at least one on the first pass,
and the check prints one line per device, on a pass too: `"concurrent tabs on <device>: N tabs, A
loaded on the first pass, B on their reload, C not at all"`. `runLiveBackendRestartRecovery` stops
the twin under an open page once its landing section has answered, waits for the section's banner,
restarts the twin on the same port and config, and needs the page to recover by itself — the
banner hidden again — within the boot time plus the poll back-off cap, with no reload. The put
matrix expects exactly one word per case (`valid`, `unchanged` or `invalid`), reading each case's
current value from the twin first; it sends each never-"Unchanged" field of the sensors section
twice, both Valid, and drives the four action fields through the page with probes of their own,
in this order: `ResetErrors` (its confirmation answered, then every error-count row read as `0` in
place), `LightCmdLED` (lit for 10 s, a second send answered Failed while it runs, an out-of-range
one Invalid), `PauseTime` (two sends Valid, the remaining time read on the status page, 3601
Invalid) and `SystemCmd`'s `mempause` last, since a `ResetErrors` while it holds storage answers
Failed. `reboot`, `bootloader`, `resetconfig` and `erasefram` end the twin process, so the unit
tier's shutdown scenarios (A.8) cover them, not this tier. Before the reset, `archiveErrcount()` keeps
`GET /status`'s error counts under `build/archive/live_twin/` (`scripts/_archive_evidence.py`, one
run directory per test process). Captions are checked against `tests_js/_expected_display.js`, the
text the page should show, written apart from `js/field-format.js` so the live tier never checks
the renderer against itself (`tests_js/expected-display.test.js` pins it to hand-written texts).
Every live command fails on a twin whose output holds a memory marker or a restart sign
(`SimulatedResetError`, `reboot triggered`; `tests_js/_memory_markers.js`). The matrix page runs
with reduced motion, which removes only the drawer's slide, and waits for each element on the
frame it appears, then confirms it with the same locator wait (agent, 2026-10-13, decided on the
owner's behalf for review); its three CI shards took 245-255 s each (2026-10-13).
""",
)

# X37: H.7's cross-browser paragraph, the full ceiling.
edit(
    """`tests_js/live-backend.test.js`'s `runLiveBackendConcurrentTabs` (`max_connections // 2` parallel
Chromium tabs against one twin, so the ceiling is never exceeded; every tab must load).""",
    """`tests_js/live-backend.test.js`'s `runLiveBackendConcurrentTabs` (the device's whole
`max_connections` of parallel Chromium tabs against one twin, every tab loading on the first pass
or on one reload of its own).""",
)

# H.8: the test list gains the display oracle and the restart signs.
edit(
    """its code table against the mock's; `tests_scripts/test_js_api_mirrors.py` pins every JS copy of a
`src/` wire fact (G.2).""",
    """its code table against the mock's; `tests_scripts/test_js_api_mirrors.py` pins every JS copy of a
`src/` wire fact (G.2). `tests_js/expected-display.test.js` pins the live tier's display oracle to
hand-written texts, and `tests_js/memory-markers.test.js` the twin's restart signs beside the memory
markers (H.7).""",
)

# H.8.1: the shared display oracle follows the convention.
edit(
    """excess-property checking, is the worked example). **Testing an async DOM refresh**: poll for the""",
    """excess-property checking, is the worked example; `tests_js/_expected_display.js`'s `DisplayField`,
in the one test module both contexts import, follows it too). **Testing an async DOM refresh**: poll
for the""",
)

for old, new in EDITS:
    count = text.count(old)
    if count != 1:
        sys.exit(f"found {count} times:\n{old[:300]}")
    text = text.replace(old, new)
SPEC.write_text(text, encoding="utf-8")
print(f"applied {len(EDITS)} edits")
