"""Lane X resume: the live tier's two Part N rows beside the l0.live_twin_* rows."""
import sys
from pathlib import Path

SPEC = Path(sys.argv[1])
lines = SPEC.read_text(encoding="utf-8").split("\n")
hits = [i for i, line in enumerate(lines) if line.startswith("| `l0.live_twin_tab_wait_ms` |")]
if len(hits) != 1:
    sys.exit(f"anchor: {len(hits)} hits")
rows = [
    "| `l0.live_concurrent_tabs_timeout_ms` | 200000 ms | `tests_js/live-backend.test.js` — `200000` | the full-ceiling tabs case per device: the twin's boot (`l0.live_twin_ready_timeout_ms`), the first pass within the page's request cap (`web.outer_cap_s`) plus 5 s, one reload of up to `l0.live_twin_tab_wait_ms` per tab of `max_connections`, the stop | estimated (agent, 2026-10-13): the sum of those waits, 20 s, 20 s, six 20 s reloads and the stop — measurement owed: elapsed per device on the slowest host that runs it, L0 (the JS tier); here 10.2-23.2 s per device, one run of all six (2026-10-13) | about 8.6× the slowest device here | `max_connections`, `web.outer_cap_s` or a wait it sums changes |",
    "| `l0.live_restart_recovery_timeout_ms` | 180000 ms | `tests_js/live-backend.test.js` — `180000` | the restart-recovery case per device: two boots (`l0.live_twin_ready_timeout_ms`), the banner wait (`l0.live_twin_section_wait_ms`), the back-off cap the page may be waiting out (`web.poll_backoff_max_ms`), two stops and their drains | estimated (agent, 2026-10-13): two 20 s boots, the 10 s banner wait, the 60 s back-off cap and two stops with their drains — measurement owed: elapsed per device on the slowest host that runs it, L0 (the JS tier); here 6.3-9.3 s per device, one run of all six (2026-10-13) | about 19× the slowest device here | `web.poll_backoff_max_ms` or a wait it sums changes |",
]
at = hits[0] + 1
lines[at:at] = rows
SPEC.write_text("\n".join(lines), encoding="utf-8")
print("live rows applied")
