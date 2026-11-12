# R5 unit giveup: every bound on a wait, traced to its source (lead, 2026-11-09; read-only, three passes)

## Read first
`S/u35r/r1/common_r1.md` (binding; above all its new paragraph "A bound needs a source" and the filter rule; labels
`giveup1_` .. `giveup3_` by pass). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
Tree `S/wt-u35int` at 8f04f2f1, read only. Then FINDINGS 12.131 and 12.133 (the LED example), 12.105, 12.107, 12.129;
`S/u35r/r5/CPRIM.md` (polls) and `SIMPLER_1.md`-`SIMPLER_4.md` (routed already: cite, never redo); `BRIEF_B.md` and
`BRIEF_FSYNC.md` (units writing now: a site their items already change is marked "in B" / "in fsync", not judged again).
Owner rulings on bounds bind and are never re-proposed: grep `S/u35r/recovered/owner_rulings_after_LN118.md` for
timeout, retry, deadline, interval, timer (filtered); known ones: UART 1,000 ms timeout and recovery timings (2026-09-11,
2026-11-03 "Keep the UART as is"), NTP's 60 s unsynced retry (11-03), FRAM setup's up-to-three RDID reads (10-28), the
1 s status pass deadline (10-28), the reset timer (2026-07-18), I2C wedge and Wi-Fi false positive left to the watchdog
(CLAUDE.md), Part N's register scope (11-04 11:23).

## Owner (verbatim)
- 2026-11-09 21:57:36: "So the timeout and give up of the LED was just one more example of how overkill grew into the
  audit, although smart simplicity was the target. Yet another pattern example, be sure to find all of such occurrences."
- 2026-11-09 21:36:14: "... I don't think anything like this timeout and give up mechanics ever existed in the original
  firmware, or did it? Sounds pretty much like that overkill again, have a check, and find a solution without that many
  magic numbers and which generalizes cleanly."

## The pattern
A bound on a wait or on work: timeout, deadline, `wait_for`, a `ticks_diff` compare, retry or attempt count, backoff,
expiry or staleness window, a drop or give-up, a size or queue cap that drops, a rate limit, a software timer standing
in for a backstop - and the number it uses. The LED's case: an internal request waited on the device's own state, gave
up after 120 s and was dropped silently; legacy had no such bound; the fix is one FIFO lock, no number at all.

## Per site
Construct; whose failure it bounds (outside party: network peer, UART peer, a chip whose datasheet bounds it / inside:
the device's own lock, task, queue, event); origin (original firmware: `python/` or `legacy/`, compared by reading /
refactor before 2026-10-06 / audit from 2026-10-06; earliest commit by `git log -S`, with `':!arduino'`, and whether a
session or the owner authored it); its source of need (datasheet page, Part J, Part F fact, owner ruling verbatim with
date, legacy behaviour, none); what happens at the bound (logged, silent drop, retry, degrade). Verdict: KEEP (source
named, number derived) / DERIVE (needed, number magic: derive it from its source or name the source) / REMOVE (inside
wait, or a duplicate of another backstop - watchdog, supervisor, the peer's own timeout - or no source at all: the
simpler form, what goes, what stays, why no function drops and no gap opens) / ASK (user-visible behaviour, an owner
ruling, a UART wire or recovery timing (Class A), or a possible feature) / NOTBOUND (the match is not a bound).

## The three passes (one agent each)
1. Network and link: `src/asy_uart_driver.py`, `asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py`,
   `asy_wifi_service.py` (identifier matches only), `asy_webserver_service.py`, `asy_ntp_client.py`, `asy_dns_client.py`,
   `asy_udp_socket.py`, `asy_captive_dns.py`; the website `js/` and `html/`.
2. Drivers, system, logging, generation: every other `src/` module; the generated modules (filtered); `buildgen/`'s
   tunables, defaults and validate rules; the device TOMLs' timing keys (filtered); Part N's firmware and buildgen rows.
3. The apparatus: `scripts/`, `toolchain/`, `.github/`, `buildgen/` host code, `digital_twin/` runtime, `tests/` shared
   helpers (`_*.py`, `microtest.py`), `tests_hardware/` harness, conftest and device scripts, `tests_scripts/` and
   `tests_js/` helpers; per-test waits by mechanism counts, not per site. CLAUDE.md's hang backstop (timeout + retry +
   line buffering) and the `uv sync` retry are owner rules: KEEP, cited.

## Completeness (the owner's "be sure")
Enumerate mechanically, then judge every hit: name patterns (`timeout|deadline|retr(y|ies)|attempt|give.?up|expire|
stale|_wait|wait_for|ticks_diff|ticks_add|_ms\b|_s\b|_us\b|_max\b|max_|limit|drop|backoff|tries`) and constructs (a
counter in a `while`/`for` around an operation, a sleep in a loop, `Timer(`, `settimeout`, `poll(`). Write a ledger
`S/u35r/r5/GIVEUP_<pass>_ledger.tsv`: path:line, construct, verdict, origin, source code - no source text. The hand-back
states the enumeration commands, the hit count, and that ledger rows = hits = the sum by verdict.

## Never
Never edit any tree. No runs but git and grep: no gate, no test, no probe (two writing units hold the host). No hardware.
Never read `arduino/`; never open `/root/.claude/`. Credential filter on every view or grep of `src/asy_wifi_service.py`,
generated modules, `devices/`, SPECIFICATION.md, CLAUDE.md and `audit/`; never print, copy or write any Wi-Fi credential
or the hotspot password. `python/` and `legacy/` are read for comparison only. Scratch only under
`S/u35r/r5/ftmp_giveup<pass>/`.

## Limits and hand-back
Write only `S/u35r/r5/GIVEUP_<pass>.md` (at most 60 lines; first line "giveup<pass> hand-back, written by the agent
(<date -u>)"; REMOVE, ASK, DERIVE ranked by gain against risk; one line naming what is KEEP and clean) and its ledger.
Budget about 1 % of the week each. Hand back by 01:30 UTC: its path, one line per headline result, and last "nothing of
mine is running".
