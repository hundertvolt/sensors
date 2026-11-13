# FWB: firmware services and the website

Scope: `src/asy_system_service.py`, `asy_wifi_service.py` (filtered excerpts only), `asy_ntp_client.py`,
`asy_dns_client.py`, `asy_captive_dns.py`, `asy_udp_socket.py`, `asy_webserver_service.py`, `asy_api_response.py`,
`asy_uart_comm.py`, `asy_uart_driver.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py`, `asy_neopixel_driver.py`,
`asy_notification_service.py`, plus `js/` and `html/`. Release `wt-final` at `590cffcf` against baseline `25caf528`.

## Verdict

The rulings largely hold here. Every drift pattern named in PICTURE.md section 4 and DRIFT.md 2.9 is gone from the code:
- the NeoPixel 300 s rewrite and its lost cancel;
- the LED queue's 120 s give-up;
- the notification sample-age check and `State`;
- the webserver's start retries;
- the NTP elapsed-time resync and its rounding rule;
- `ready()` on `wait_for_ms`.

Each `/status` and website addition I traced has an owner decider. Four small leftovers remain:
- the dead `except MemoryError` branch from the removed 1,200 ms escalation wait;
- typing-only `isinstance` guards in `UARTComm`;
- a dead typing Protocol member;
- the pre-audit dead length checks.

One website behaviour the agent added during the drift has no recorded decider and changes what Apply sends: the re-read
before the PUT. Nothing found contradicts a later owner ruling.

## Shape since the baseline

- **`asy_system_service.py` (397 to 725 lines).** Added, all with owner deciders:
  - the `mem_backup` reset-reason and boot-phase record (owner, 09-26);
  - the controlled shutdown and the `resetconfig`/`erasefram` commands (09-30, OR119/OR121);
  - the forward-only phases (O4 topic E, 11-12);
  - the C-stack reboot (review page);
  - the config flush before reset;
  - the timer stagger as deadline sleeps (the Timer chain is gone) and the measured uptime;
  - `LastTaskEnd` (OR128), `ConfigFaults` (10-01) and the unretrieved-exception report (10-07, guard confirmed 11-02).
- **`asy_ntp_client.py` (483 to 448).** Three Timers became `TickGrid` tasks. The stale check now uses the measured
  sync age (a real fix: the pre-audit counter never reached it). The unsynced retry is 60 s (owner, 11-03). The
  NTPHost/DNSFallback shape checks were added, and `NTPSynced` is the only flag (11-06).
- **DNS client, captive DNS and UDP socket (all smaller).** One shared IPv4 helper, loggers passed through (owner,
  11-02 (d)), and the receive back-off chain collapsed into one 3 s wait.
- **`asy_webserver_service.py` (807 to 1015).** Added:
  - WS-1's head bounds and the `Content-Length` check (WS-2's other refusals are gone, 10-28);
  - the `_PieceWriter` flat rule with per-value yields and one `/status` build at a time (owner, 11-06);
  - `HTTPDropped` (10-01), the `ResetErrors` refusals (10-13) and the LED-busy descr (10-02);
  - a static `Content-Length`, and the rebinding of `microdot.print_exception` for silence at level 0.

  The start retries are gone, so the supervisor restarts the server.
- **UART.**
  - The driver (455 to 857) received the DMA receive ring and `PieceBuffer` (owner, 10-05) and the clamped reads.
  - The link driver (160 to 308) received hazard mode (owner, 10-21; its form is the agent's) and its `/uart` route
    (O4 topic I).
  - `UARTComm` stayed about the same size, with the receive cap and a write hold-off that survives a ticks wrap.
- **LED.** NeoPixel went from 187 to 150 lines: one task and one lock. Its FRAM log was dropped (owner, 11-09: "no
  logger at all"). The notification service went from 376 to 277 lines: `register()`/`finalize()` are gone,
  `Triggered`/`TS` left `/status` (owner, 11-03), and the pause is measured (OR104).
- **Website.** Added:
  - `shell.js`, with the device clock (OR94 15a), the auto-reload on a new build (review "ok") and the Back history
    (review note);
  - the clickable codes and code tones (OR94, CalLight table), decimals (10-02), confirmations, the inert drawer and
    reduced motion (accessibility review);
  - the contrast tokens (OR132 2a), the unavailable marker and the restored legacy favicon (owner-reviewed 10-02).

## Findings

### FWB-1 [L, with a G side effect] [VERIFIED] The website's Apply re-reads the section before the PUT, so it sends toggles and selects the user never touched
- **Where:**
  - `js/render.js:204-207` (the re-read before the form is read);
  - `js/render.js:607-631` (`fetchOnce()`; it also fetches `/status` when a group reads it);
  - `js/render.js:422` and `:471` (a toggle or enum is sent when it differs from the baseline);
  - `js/templates.js:924-951` (`updateFieldGroupValues()` never repaints an editable toggle or select);
  - `js/render.js:726` (settings sections poll once).
- **What:** before reading the form, Apply now GETs the section (plus `/status` where needed), and that fresh read
  becomes the baseline. The page itself, however, keeps showing toggles and selects as they were at the last GET.
  - **Trigger:** another client (a second tab, a phone, any API client) changes a toggle or enum after this page's
    last GET.
  - **Result:** `collectGroupBody()` sees the untouched, stale control differ from the fresh baseline and sends it.
    This silently reverts the other client's change, and the device persists that write to flash.
  - **Pre-audit behaviour** (`25caf528` `js/render.js:201`): the baseline was the values the card was built from, so
    an untouched control was never sent. That is the sparse-PUT rule in H.4: "a plain toggle or enum when it differs
    from its baseline", meaning only what the user changed.
  - **Cost of the re-read:** one or two extra GETs per Apply, `/status` (the heaviest route) among them, on top of
    the post-write GET.
- **Ruling/pillar it meets:**
  - 10-28 "building upon hypothetical findings is a clear no-go", since no observed failure motivated it;
  - P9 and OR42 "write only on change";
  - L7, agent text bound as behaviour.
- **Decision record:** none found. It was added in U23 (`9bf22747`, 2026-10-13) as agent text: "Apply refreshes the
  section before reading the form". SPECIFICATION.md H.4's "PUT/GET error handling" row names no decider, and the
  row "Divergences from the legacy site", which says it lists every departure with its decider, omits it.
- **Smallest fix:** delete `js/render.js:204-207` and keep the post-write GET at `:146`. Owner must decide, because the
  WYSIWYG reading ("what the page shows is what Apply sets") is a possible intent.

### FWB-2 [L] [VERIFIED] The escalation entry's `except MemoryError` is the residue of the removed 1,200 ms escalation wait
- **Where:** `src/asy_system_service.py:544-550`.
- **What:**
  - On `72b12815` (2026-10-21), this `try` wrapped `await asyncio.wait_for_ms(entry, _ESCALATION_ENTRY_WAIT_MS)`
    and caught `TimeoutError` plus a `MemoryError` from "building the entry, its wait or its write".
  - The cleanup made `err_s()` synchronous and removed the wait and the `TimeoutError` arm, but kept the `MemoryError`
    arm. It now guards one log call.
  - The reset code is already written before it (`:539`), and the command gate already refuses (`:538`). Without the
    arm, a `MemoryError` reaches the supervisor's own top (`:564-566`), which logs it and ends unfed. The watchdog then
    resets with the same recorded code.
  - The only thing lost is the config-store flush inside `_reboot()`, and that matters only for a PUT staged in the
    same instant on a heap too exhausted to format one log line. No observed trigger.
- **Ruling/pillar it meets:**
  - DRIFT 2.9, "the C-stack escalation: about 120 report calls and a bounded escalation wait" (a cascade root);
  - L2/L3, "a mechanism for a trigger nobody observed is not wanted" (the ladder carries it);
  - 11-11 "no runaway chains".
- **Decision record:** none from the owner. SPECIFICATION.md F.2 carries the agent sentence "a `MemoryError` building
  it still arms the reset" (around line 6660). The C-stack reboot itself is decided and is not in question.
- **Smallest fix:** drop the `try`/`except MemoryError` (keep the two `err_s()` calls), plus the F.2 clause.

### FWB-3 [L] [VERIFIED] Typing-only `isinstance(..., int)` guards in `UARTComm`'s configuration and argument checks
- **Where:** `src/asy_uart_comm.py`:
  - `:231-235` (`__init__` "re-checked locally ... `5 + "48"` raises");
  - `:916` and `:922` (pre-audit);
  - `:924`, `:933` and `:935` (added in the audit, `c11ca0aa`, 10-08);
  - `:431` and `:443` (pre-audit).
- **What:** every guarded value is annotated `int`, and every in-tree producer is a validated int:
  - `TransferLimits` is generated from the module's own int constants plus `max_transfer_bytes`, which goes through
    `_checked_int` (`buildgen/codegen.py:553-561`, `buildgen/validate.py:914`);
  - the bus kwargs are refused at build time unless ints (`buildgen/validate.py:813-815`);
  - the command ids are literals.

  So each `isinstance` clause is fully covered by typing alone and unreachable today, which is the owner's two-part
  test. The range halves are real (byte truncation, J.6 floors) and stay. The callback-result checks (`:304`, `:366`,
  `:624`, `:663`) are not in this finding: the callbacks are typed `object` on purpose (`:31-53`).
- **Ruling/pillar it meets:**
  - owner, 2026-10-27: "if the check you remove really solely covers typing breakages and nothing else it can go";
  - PICTURE M4;
  - 11-07: the lens applies to pre-audit code too.
- **Decision record:** the owner's 10-27 rule. Nothing specific to these sites was found.
- **Smallest fix:** delete the `isinstance(...)` clauses and keep the range comparisons. `__init__`'s two fallback
  lines (`:234-235`) reduce to the plain attribute values.

### FWB-4 [L] [VERIFIED] A dead typing Protocol member: `_RequestLike.sock` and `_Holder`
- **Where:** `src/asy_api_response.py:24-25` and `:33-34`.
- **What:** a typing-only stand-in for a request socket pair with a `hold()` method. Nothing in `src/`, `tests/`,
  `digital_twin/` or `buildgen/` reads `request.sock` or calls `.hold(`; a `git grep` finds only these definitions.
  It is a leftover of a removed connection-holding mechanism and does not exist at baseline.
- **Ruling/pillar it meets:** "dead code" (brief class L); P4.
- **Decision record:** none found.
- **Smallest fix:** delete `_Holder` and the `sock` property.

### FWB-5 [E] [VERIFIED] Unreachable length checks on `ConfigManager` getter results (pre-audit)
- **Where:**
  - `src/asy_notification_service.py:217-219`;
  - `src/asy_ntp_client.py:183`, `:283`, `:412`, plus `:428` (`len(cet) == _GMTIME_FIELDS`) and the constants `:87-89`.

  The same shape appears outside this scope in `asy_sgp40_driver.py:253` and `:321` and `asy_bmp3xx_driver.py:187`
  and `:234`.
- **What:** `ConfigManager._get_values()` returns exactly one value per schema name or `None`
  (`src/asy_config_manager.py:357-367`), so a length mismatch cannot occur. `time.gmtime()` always returns 8 fields.
  The `None` checks are the real ones.
- **Ruling/pillar it meets:** 11-07 "could the same outcome be implemented leaner without losing anything"; 10-27 "a
  strong hint ... unreachable with today's code".
- **Decision record:** none found.
- **Smallest fix:** drop the `len(...)` clauses and the three count constants; keep the `None` checks.

### FWB-6 [L] [SUSPECTED] Small visible website changes with no recorded decider
- **Where:**
  - errcount count colour by severity: `html/style.css:469-481`. Pre-audit coloured any non-zero count red (`25caf528`
    `style.css:407`); now warnings-only rows show in the warn colour and rows without data in muted italics.
  - a new "Resolution:" hint line under every field with a resolution: `js/templates.js:448-450`.
  - a browser `console.error` printed once per failing episode: `js/render.js:646-650`.
- **What:** each one changes what the page shows. None is in H.4's "Divergences from the legacy site" row (which says
  it lists every departure with its decider), and none is among the owner-requested items in PICTURE sections 4 (M13)
  and 5. The "no data" and "unavailable" row text is not part of this finding: it fixes the old healthy-zero fallback.
- **Ruling/pillar it meets:** OR94 "don't change the current look of the website".
- **Decision record:** none found. The owner's 2026-11-06 "Question 10: Keep all of it" (web server and website) may
  cover them, but I could not see the Q10 list.
- **Smallest fix:** owner decides. If not covered, restore the pre-audit count colour and drop the hint line.

## Checked and clean

- NeoPixel: the 300 s overlay rewrite and its lost-cancel cascade are gone. Now there is one signal task and one lock,
  and the overlay waits as it did before the audit (`asy_neopixel_driver.py:95-103`).
- LED queue: the 120 s deadline and give-up are gone. An internal request waits on the lock; every ramp is finite
  (`:137-147`).
- The two 10,800 s sample-age checks: none remain in scope. Notification's `State`, `Triggered` and `TS` are gone
  (owner, 11-03).
- 1,200 ms escalation wait: removed. Only the `MemoryError` arm remains (FWB-2).
- Webserver: the three retries 5 s apart are gone. A failed start raises and the supervisor restarts it (`:896-901`).
- NTP: the due check is counted again (`:294-298`), with no elapsed-time resync and no rounding rule. The stale check
  on the measured age fixes a real pre-audit gap.
- UART: `ready()` polls with `sleep_ms` and its one yield (`asy_uart_driver.py:743-784`). `wait_for_ms` is gone, and
  `cancel_read_timeout()` lost its timeout.
- UART and FRAM coupling: `err_s()` is synchronous and never suspends, the DMA ring receives through FRAM and flash
  holds, and nothing waits on a FRAM lock (owner, 11-07, option B). `_FLASH_HOLD_MAX_MS` sizes the ring against
  internal flash, not FRAM.
- Per-episode log flags: Wi-Fi's per-state-change line is owner-decided (11-06); notification's override transition
  line is pre-audit.
- Console lines for caught `MemoryError`s go through the user's or builder's logger (UDP, UART driver, COBS, DNS),
  which the owner decided on 2026-11-02 (d). The exception-handler-only-if-unset guard (`asy_system_service.py:695-699`)
  was confirmed by the owner on 11-02 ("That's okay").
- No `asyncio.wait_for(` in scope. The webserver's `wait_for_ms` is the per-call and outer cap (owner and agent,
  08-12).
- Webserver head handling: the head bounds (WS-1) and the `Content-Length` check are kept; WS-2's other refusals,
  including the version refusal, are gone (owner, 10-28).
- `/status` and website additions have deciders: `LastTaskEnd` (OR128), `ConfigFaults` (10-01), `HTTPDropped` (10-01),
  `MemFree` (09-26), `UnixTime` (OR94 15a), the reset reason (09-26/10-02), the system commands (OR121) and the UART
  Link section (O4 topic I).
- Website items the owner asked for are all present and in a small form: code tones, the inert drawer, the
  section-switch hand-over (`render.js:595-603`, `:741-756`), contrast tokens, Back history, decimals, confirmations,
  auto-reload and the device clock. The favicon is the legacy one restored (owner-reviewed, 10-02).
- No test hooks in the shipped website (`js/main.js` and everything it imports; `js/app.js` and the mock are never
  staged).
- The UART wire format is unchanged by anything flagged here: FWB-3 touches only receiver-side configuration checks
  and emits the same bytes.

## Notes

- `buildgen/validate.py:871-990` re-implements `UARTComm`'s J.6 formulas: the `rxbuf` floor, `rx_ring` floor, poll
  range, minimum and maximum timeout, and transfer cap. These are already in `asy_uart_comm.py:566-600` and
  `:911-939`. The constants are single-sourced and the formulas are copied. The mirror is pre-audit and was extended
  by the audit; whether one side should go is an owner call (P8 against build-time errors).
- The device watch GETs `/status` every 60 s on sections without status fields, only to refresh the clock offset from
  `UnixTime` (`js/shell.js:96-103`). `/status` is the heaviest route; worth a look under the 11-07 lens, but not a
  clear gain.
- Hazard mode (`asy_uart_link_driver.py:46-72` and `:128-239`) is test machinery inside dev's firmware. It is
  dev-only and owner-accepted (O4 topic I; the 11-07 08:42 go to widen its wait).
- `UART.read_until_complete()` and `UART.readline_until_complete()` have no product caller; they are library features
  (owner, 11-09: ask before removing).
- `WebserverService.get_error_sources()` is documented as unused (`asy_webserver_service.py:960-964`).
- `asy_uart_comm.py:342`'s comment says the line exists "for the memory gates". The line itself is owner-decided
  (11-02 (d)); only the test-facing wording is left.
- `asy_uart_link_driver.py:16` imports the private `_body_as_dict` from the webserver. It could live in
  `asy_api_response.py` with the envelope.
- M1's sentence ("only worth closing for a concrete, non-hypothetical threat") is not in SPECIFICATION F.2 or I.4(a)
  verbatim; I.4(a) carries "expectable memory errors". This is for the docs scan.
- Already-decided items were not re-raised: the Wi-Fi behaviour as built, the C-stack reboot, the boot `gc` placement,
  the UART wire format, the hotspot fallback, `ext/`, and dev's bench quirks.
