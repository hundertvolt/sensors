"""Lane X edits, part 3: Part N rows (each anchor row found exactly once; new rows inserted after it)."""
import sys
from pathlib import Path

SPEC = Path(sys.argv[1])
lines = SPEC.read_text(encoding="utf-8").split("\n")


def row_index(row_id: str) -> int:
    hits = [i for i, line in enumerate(lines) if line.startswith(f"| `{row_id}` |")]
    if len(hits) != 1:
        sys.exit(f"row {row_id}: {len(hits)} hits")
    return hits[0]


def insert_after(row_id: str, *rows: str) -> None:
    at = row_index(row_id) + 1
    lines[at:at] = list(rows)


def replace_in_row(row_id: str, old: str, new: str) -> None:
    i = row_index(row_id)
    if lines[i].count(old) != 1:
        sys.exit(f"row {row_id}: {old!r} found {lines[i].count(old)} times")
    lines[i] = lines[i].replace(old, new)


# X47-X49: the website's JS-only web.* rows beside web.outer_cap_s (Firmware table).
insert_after(
    "web.outer_cap_s",
    "| `web.poll_backoff_max_ms` | 60000 ms | `js/poll-manager.js` — `60000` | after the k-th consecutive failure of a section's GET the next attempt comes min(interval × 2^(k−1), this cap) later, back to the interval after one success (`tests_js/poll-manager.test.js` reads it with `readIntConst()`) | estimated (agent, 2026-09-30) — measurement owed: the time a page takes to recover once the device answers again with its sections at the cap, the L2 live restart-recovery test | one request per minute per failing section against the ~2.2 requests/s the server sustains (H.7) | `web.poll_interval_ms` or the served throughput changes |",
    "| `web.device_watch_interval_ms` | 60000 ms | `js/shell.js` — `60000` | the shell's device watch: `GET /status` for the device clock, `GET /system` for the build compare, a changed build reloading the page once no Apply is pending; one extra watch runs when a section's failure episode ends, none while the tab is hidden (`tests_js/shell.test.js` reads it with `readIntConst()`) | estimated (agent, 2026-09-30) — measurement owed: the time a page open across a reflash takes to reload, the L2 live restart-recovery test | two requests per minute per tab against the ~2.2 requests/s the server sustains (H.7) | `web.poll_interval_ms` or the served throughput changes |",
    "| `web.clock_mismatch_s` | 5 s | `js/field-format.js` — `5` | an epoch value up to this far ahead of the page's estimate of the device clock reads \"0 s ago\", further ahead \"clock mismatch\" (the age display, H.4's \"Divergences from the legacy site\" row) | estimated (agent, 2026-10-13) — measurement owed: the `/status` latency under load, L2 (the shell's `nowS()` is `floor(Date.now()/1000 + offset)`, the offset taken when a `/status` answer arrives, so it trails the device by that request's latency plus up to 1 s of flooring) | unknown until measured | the device-clock derivation or the request path changes |",
)

# X4: web.default_decimals beside web.poll_interval_ms (Build table).
insert_after(
    "web.poll_interval_ms",
    "| `web.default_decimals` | 2 decimals | `buildgen/definitions.py` — `2`; `tests_scripts/test_buildgen_definitions.py` — `2` | the top-level `defaultDecimals` of every device's definitions, taken by every fractional value of a field with neither its own `decimals` nor a `resolution` (H.5.1); `js/definitions.js` refuses one outside 0..`MAX_DECIMALS` | owner decision (owner, 2026-10-02), asked about \"How timestamps, codes and numbers show on the website\": 'Fine, and maintain a reasonable number of digits per value (e.g. limit to 2 or 3 digits behind the decimal point, don't print full floats). But only for the website, the API delivers full resolution. Configured in the website config file, derived or defined from the value sourcing modules (e.g. Schema or inside the commented configs).'; the value is the lower of the owner's two (agent, 2026-10-13) | a value that needs another precision states its own `decimals` or `resolution` (SCD30's do, H.5.1) | a displayed value whose source states no decimals needs another precision |",
)

# X50: l0.section_render_wait_ms beside the l0.render_* rows (L0 table).
insert_after(
    "l0.render_banner_wait_ms",
    "| `l0.section_render_wait_ms` | 5000 ms | `tests_js/accessibility.test.js` — `5000`; `tests_js/generated-definitions-render.test.js` — `5000`; `tests_js/site-functions.test.js` — `5000` | the wait for a rendered section's heading and every card, per device | measured (agent, 2026-10-13): the slowest section case 59 ms, `startApp` included, over 42 accessibility cases, two runs at nice 19 | about 85× | the mock gains a delay, or more requests come before the first paint |",
)

# X51: the site-functions sites of the two shared render waits.
replace_in_row("l0.render_wait_timeout_ms", "`tests_js/render.test.js` — `2000` |", "`tests_js/render.test.js` — `2000`; `tests_js/site-functions.test.js` — `2000` |")
replace_in_row("l0.render_poll_ms", "`tests_js/render.test.js` — `10` |", "`tests_js/render.test.js` — `10`; `tests_js/site-functions.test.js` — `10` |")

# X2: the spin bound reads the window's fastest round.
replace_in_row(
    "l1.lwip_host_spin_round_max_us",
    "| one `drain()` round at the patched edge (a `write()` returning `None`, a timeout-0 poll), which on this host includes select's 1 ms `poll()` sleep (F.7 row 30); rounds that ran a collection are counted and left out |",
    "| the fastest of every `l1.lwip_host_spin_window_rounds` consecutive `drain()` rounds at the patched edge (a `write()` returning `None`, a timeout-0 poll; each on this host includes select's 1 ms `poll()` sleep, F.7 row 30); rounds that ran a collection are counted and left out |",
)

# X1: the window's length, after the bound it serves (L1 table).
insert_after(
    "l1.lwip_host_spin_round_max_us",
    "| `l1.lwip_host_spin_window_rounds` | 3 rounds | `tests/lwip_host/test_modlwip_eagain.py` — `3` | the spin test reads `l1.lwip_host_spin_round_max_us` against the fastest round of every run of this many consecutive measured rounds (sliding; rounds that ran a collection are left out); the two window cases `test_one_or_two_late_rounds_pass_the_spin_window` and `test_a_round_that_sleeps_every_time_fails_the_spin_window` | owner decision (owner, 2026-10-13), asked whether the host-only test's spin-round bound, failing on single late wake-ups of this machine, should (a) stay as is, every failure going to the owner, or (b) apply the same 20 ms bound to the fastest of each three consecutive rounds: \"Then option b is fine.\" (after \"And the fix within this question is about the reliability of a test only on your local machine?\" was answered yes) | one or two late rounds in a row pass, three consecutive rounds over the bound fail, as every round of the unpatched path does (its 50,000 µs sleep); measured slowest windows 1,154-1,294 µs against single rounds of 2,288-5,471 µs, three runs at each GC stage (2026-10-13) | the host class changes, or the override or the pin's `modlwip.c` changes |",
)

SPEC.write_text("\n".join(lines), encoding="utf-8")
print("Part N rows applied")
