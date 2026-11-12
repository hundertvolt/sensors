# CRr2b5: finish the clears mechanism with its sets; CRr2b4's three finds; then the bleed and the scanner (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2b4_clears_bleed_sets.md` (the task: its rulings and
items apply) and the hand-backs `S/u35r/handbacks_redo/CRr2b3.md` and `CRr2b4.md`. Worktree `S/wt-u35crr2b`, branch
`audit/u35-crr2b` at 575f8c22, with CRr2b4's work UNCOMMITTED in it (three files, 97 insertions, 20 deletions). Logs
in `S/u35/laneC/crr2b5/`; CRr2b4's in `S/u35/laneC/crr2b4/`.

## Why CRr2b4 stopped (binding for you)
The classifier refused one Bash call that chained an inline python3 edit with `[ -d "$P" ] && rm -r "$P"` (its own
plant tree). It was not retried, and the refused call did not run. Every deletion is its own Bash call, never chained
with anything. Leave `S/u35/laneC/crr2b4/plant_i1` where it is: the lead holds it. Make your own plant tree under
your log dir. Run every plant run through `S/u35/lead/run.sh` (namespace, RUNS.md lines). CRr2b4's plant run went
outside it once, a deviation. If any command is refused, stop and hand back.

## Items, in order
1. Review CRr2b4's uncommitted diff yourself (`git diff`); keep what is right, fix what is not, say which. Make the two
   test fixes the refused call meant to make, with the Edit tool: the two-clear test's entry erased by the first clear
   (WIFI W WLAN_TO_HOTSPOT in the first pre-clear read only), and the plant's corrected expected list. Then re-run
   the nine plants, all caught.
2. Apply CRr2b4's researched sets (its hand-back, "Item 1's sets") and re-derive the five it did not reach
   (test_an_incomplete_command, the UART hazard run, serving_heap per-source, escalation, stack exhaustion) from
   each device script read in full and every src site it reaches. Each set carries its lines in your map. The
   mechanism and the sets land in ONE commit, with the README's "The bench log check" text updated (it still says a
   clear hides what came before it), after lint, the mypy passes, the readers and collect-only are green.
3. CRr2b4's three finds, the lead's rulings (test code, no wear, the lead's call):
   - test_wifi_networking.py:97 provokes and asserts NTP E NTP_NO_REPLY: it gets provokes_log with that entry.
   - network_resilience's NTP garbage test: its payload's first byte 0xff gives LI=3, so the client always logs W
     NTP_UNSYNC_REPLY (asy_ntp_client.py :324) and never the E NTP_MALFORMED/NTP_IMPLAUSIBLE its assertion names. It
     passes only through a console-line alternative. Find out first whether src prints that console line at all (cite
     the line, or say none does). Then make the test name what it provokes: either one payload per path, each asserting
     its exact code (an unsynchronised reply -> W NTP_UNSYNC_REPLY; a short or malformed reply -> E NTP_MALFORMED; an
     implausible time -> E NTP_IMPLAUSIBLE), or the one payload with its true code. An assertion with an alternative
     that can pass without the path it names goes. Its marker set follows.
   - memory_stress's extended hammer: one client more than the connection ceiling, yet it asserts every FRAM-backed
     logger empty, and WEBSERVER is FRAM-backed on dev. Run the test through the twin (`--twin`) and read src to find
     whether HTTP_REFUSED can land there. If it can, the test is wrong as written: keep its load and assert what its
     purpose needs (every logger but the ceiling's two WEBSERVER entries empty), with the CEIL set as its marker. If it
     cannot, show why with lines. Never lower its load.
4. crr2b4's item 2 (the calibration bleed) and item 3 (the scanner's decorator text) as that brief states them.

## Notes
Commit subject `U35 lane CRr2b5: <summary>`, the two trailers; do not push. Past 80 tool calls, commit what is green and
hand back at a seam (item 2 is one commit or none). Hand-back: commits; per item the evidence with log paths; every set
(before, after, lines); the finds' outcomes; the review_rows.py counts; the files whose twin record changes; last line
"nothing of mine is running".
