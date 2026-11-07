DR4 decision review, written by the part (Wed Oct 28 11:49:40 UTC 2026)

Scope: the register's owner-review list ("Decisions taken on the owner's behalf during execution"), units U17-U23,
148 rows from `inputs/DR4_register_rows.txt` (register `inputs/REGISTER_11b66cd8.md`, ids `REG:<line>`). Read-only:
nothing in the repo, the worktrees or any earlier scan file changed; nothing ran (git, grep and file reads only;
`arduino/` excluded). New knowledge used: `PICTURE.md` 2, 4, 7, 8; `SCAN2.md` whole; `G2.md` (network, UART) and
`G3.md` (buildgen, generated code, website) in full; `G1.md`, `G4.md`, `G4b.md` by row; the first scan's `REPORT.md`
2-6, `B.md`, `C.md`, `D.md`, `E.md` by row; `DRIFT.md` 2.2-2.6; the owner record (`PROJECT_AUDIT_PLAN.md` OR rows at
`11b66cd8`, `owner_rulings_after_LN118.md`, `answers.json`, the review tsv), and `audit/sweeps/open_findings.md` at
`11b66cd8`.

How rows were split: ten rows bundle decisions that take different verdicts and are split into a/b(/c): REG:494,
:520, :555, :565, :596, :612, :615, :616, :618, :637. So 148 rows give 160 entries: 159 decisions and 1 fact.

Rule used between DIFF and OBS: a decision that *created* a mechanism on an unobserved trigger is DIFF (today it would
not be created; basis the scan row that shows the trigger unobserved or unreachable). A decision that only shapes,
tests or documents a mechanism the cleanup removes is OBS.

Wi-Fi rows are OWN throughout (the owner, 2026-10-28: "We thoroughly discussed the WiFi issues and I decided
everything already."; "WiFi stays valid."), with form notes at most. The UART wire format is a two-implementation
contract: noted, never re-decided; no entry below changes an emitted byte.

## 1. Counts

**159 decisions, 1 fact.**

| verdict | entries |
|---|---|
| SAME | 109 |
| OWN | 21 |
| SUP | 9 |
| FORM | 8 |
| DIFF | 7 |
| OBS | 5 |
| CHECK | 0 |
| fact | 1 |

Per unit:

| unit | SAME | FORM | DIFF | OBS | OWN | SUP | fact | all |
|---|---|---|---|---|---|---|---|---|
| U17 UART | 12 |  |  | 2 |  | 2 |  | 16 |
| U18 NET | 9 |  | 4 | 2 | 4 | 1 |  | 20 |
| U19 REST | 10 | 3 | 1 |  | 1 |  |  | 15 |
| U20 GEN | 21 | 2 |  |  |  | 3 |  | 26 |
| U21 TOOL | 16 |  |  |  | 1 | 1 |  | 18 |
| U22 LED re-check | 7 |  |  | 1 | 8 | 2 |  | 18 |
| U23 WEB | 34 | 3 | 2 |  | 7 |  | 1 | 47 |

Per topic:

| topic | SAME | FORM | DIFF | OBS | OWN | SUP | fact | all |
|---|---|---|---|---|---|---|---|---|
| website | 20 | 3 | 1 |  | 3 |  |  | 27 |
| docs-records | 21 |  |  |  |  |  |  | 21 |
| ci-tooling | 12 |  |  |  | 1 |  |  | 13 |
| wifi |  |  |  |  | 12 | 1 |  | 13 |
| tests-unit | 9 |  | 1 |  | 1 | 1 |  | 12 |
| process | 9 |  |  |  | 1 | 1 | 1 | 12 |
| twin | 6 |  |  | 1 | 1 | 1 |  | 9 |
| uart | 4 |  |  | 2 |  | 2 |  | 8 |
| ntp-dns | 3 |  | 3 |  |  | 1 |  | 7 |
| buildgen-toml | 7 |  |  |  |  |  |  | 7 |
| supervisor-reset-watchdog | 4 | 1 |  |  | 1 | 1 |  | 7 |
| webserver-rest | 1 | 3 | 1 |  |  | 1 |  | 6 |
| generated-code | 3 | 1 |  |  |  |  |  | 4 |
| memory-gc | 2 |  |  |  |  |  |  | 2 |
| core-logging |  |  | 1 | 1 |  |  |  | 2 |
| led-notification |  |  |  | 1 | 1 |  |  | 2 |
| error-catalog | 2 |  |  |  |  |  |  | 2 |
| tests-hardware | 2 |  |  |  |  |  |  | 2 |
| timing-waits | 1 |  |  |  |  |  |  | 1 |
| driver-scd30 | 1 |  |  |  |  |  |  | 1 |
| config | 1 |  |  |  |  |  |  | 1 |
| release | 1 |  |  |  |  |  |  | 1 |

Why so many SAME: U17-U23's owner-review rows are mostly the form of owner-asked features (website, Wi-Fi, system
commands), docs that state the tree, test and tooling details, and process rules. The in-doubt firmware mechanisms of
these units (the resolver's diagnostics, the head refusals, the build checks no TOML can trip, the browser validator)
were mostly decided in the plan's packets, not in these rows; where a row decided one, it is below as DIFF, OBS or
FORM. The seven umbrella rows ("every default of the lane plan's section 5 is the ruling") are SAME as process only;
section 8 says what that covers and what it does not.

## 2. DIFF rows

**REG:514** (U18) — topic ntp-dns; line L3 misfit (also L5)
- As taken: C.7.1's "No logging in these layers" is kept word for word, and an agent sentence beside it explains that
  the resolver writes W12 and W16 into the logger its caller passes (`pr=`) and that `UDPSocket` prints a caught
  `MemoryError` through `console()`.
- New answer: the rule constrains the code, not the reverse. The resolver returns its sentinel and its one caller
  logs (the pre-audit shape); UDP keeps its catches without console lines; the agent sentence is not needed.
- Basis: the pre-audit rule, `SPECIFICATION.md@25caf528:1939`: "Deliberately no logging — every failure surfaces to
  exactly one upstream owner." S2-G2-5: the `(address, cause)` and `pr=` widening is K, order 2, for one product
  caller (`asy_ntp_client.py:415`), minimal form `resolve_ipv4() -> str | None` with no logger; G2's families table:
  "a logger passed into a logger-less layer ... the pre-audit C.7 bool rule: the layer returns its sentinel, the caller
  logs". S2-G2-3: UDP's console lines are H (P4), no product reader; the owner chose test-side logging for the memory
  gates ("Option 1 is good", 2026-10-20, as SCAN2 section 3 cites it).
- What changes: SPEC C.7.1's agent sentence (about 6 lines) goes; resolver about 30 device lines go, about 3 stay
  (S2-G2-5), catalog E73, E74, W16 retire or go (S2-G4X-6's tombstone question); UDP about 14 console lines go
  (S2-G2-3's UDP part). Tests: about 8 resolver and 5 UDP test functions (G2's name greps).

**REG:511** (U18) — topic core-logging; line L2 misfit
- As taken (OF-61's closure): after `setup()`, a failed or refused history write starts a run whose first failure
  keeps one counted `LOG_RAM_ONLY` entry in RAM; a storage pause adds one such entry per logger that logs during it.
- New answer: OF-61 stays recorded as knowledge; no run state after `setup()`. The newest-entry rule (`_keep()`) is
  the logger's one repeat mechanism.
- Basis: A-P3 (A.md): class H, "implausible (a failing FRAM after boot; the FRAM layer's own entries already show
  it)"; OF-61's own text: "(the FRAM layer's own entries cover part of it)"; G4's closure G4R07: "`_keep()` alone";
  the owner's OR35.b "No distinction ... just don't repeat the same error in the slots. Pure and simple."
- What changes: `_write_failing` and the after-setup run in `asy_print_log.py` (G1 cites `:236-238`; A-P3 counts about
  20 lines and one flag for all its arms), their tests; E28 `LOG_RAM_ONLY` stays only if the setup-time arm stays with
  the confirmed unreadable-log-store gap (A-P4, SCAN2 section 5 keep list), else it retires.

**REG:519** (U18) — topic ntp-dns; line L2 misfit
- As taken: a stored `NTPHost` or `DNSFallback` outside its shape (a hand-edited file, more than three servers) runs on
  its default with W10, as a malformed PUT is refused with E21.
- New answer: no stored-value re-check; the PUT check is the one gate.
- Basis: S2-G2-6 (verified by grep): no pre-audit file can supply such a value (`NTP_Host` renamed to `NTPHost`, no
  migration, `git grep NTP_Host 497b3eda -- src buildgen js` finds none; `DNSFallback` is new), so only a hand-edited
  file reaches it; NTP-3 copies Wi-Fi's stored-value rule without its reason (the radio API raises, the resolver does
  not); NTP-3 and DNS-1 cover each other and the PUT check covers both. The only write path is the REST PUT
  (CLAUDE.md, flash-write rule). Owner, 2026-10-28: "building upon hypothetical findings is a clear no-go".
- What changes: about 8 lines (`asy_ntp_client.py:218-223`, `_WRN_STORED_DEFAULT`; W10 stays for Wi-Fi), 3 "stored"
  test functions; SPEC C.8's "at most three servers" then rests on the PUT check (one clause).

**REG:520b** (U18) — topic ntp-dns; line L1 misfit
- As taken: a heap failure while parsing a captive-DNS query or its sender is re-raised to `run()`, persisted as E23
  `UNEXPECTED` with its text, and the listener backs off 3 s, "instead of being dropped as malformed".
- New answer: the parse keeps the pre-audit catch: a failed parse, heap failure included, is a malformed query.
- Basis: S2-G2-10: class K ("diagnostics, nothing observed"); in captive DNS it is "more than a log: run() persists E23
  and pauses the listener 3 s per heap failure in hotspot mode"; the premise "swallowed" does not hold:
  `captive_dns.py@25caf528:123-124` logged the warning "Invalid DNS request data or address, not sending response."
  and backed off.
- What changes: 2 lines (`asy_captive_dns.py:185-186`) and their test. The other half of this row (one yield per
  datagram, REG:520a) stays: confirmed gap.

**REG:531** (U19) — topic webserver-rest; line L2 misfit
- As taken: the head guard also refuses a request-line version without "/", because Microdot "would otherwise raise an
  `IndexError` and print a traceback".
- New answer: not added; WS-1's bounds stay as the head's one guard.
- Basis: WS-2 (B.md): H, "implausible: on the trusted LAN ... a non-numeric length raises inside Microdot's own catch";
  S2-G2-8: WS-2's motive (no client-triggered print) is WS-9's, and Microdot's catch already ends the connection;
  the print itself is level-gated through the kept rebind (FORM REG:110 below).
- What changes: 1-3 lines in `_check_head_line()` (`asy_webserver_service.py:358-397`) and its matrix case; part of
  WS-2's about 32 lines.

**REG:615b** (U23) — topic website; line L2 misfit
- As taken: the reflash window between page load and the first successful watch (OF-144) is carried as work, target
  U27, "one build stamp handed to the generated module and the stager"; built later as the page build-date stamp
  (U35, `1b638f1`, `7d6d255`, closed in REG:794).
- New answer: OF-144 is recorded as knowledge, not closed with code.
- Basis: S2-G3-14: the owner-approved watch already reloads on any build change after the first one seen
  (review `website-unattended` "ok"); its first tick runs at page start (`js/poll-manager.js:174-176`), so the stamp
  only covers a reflash landing inside one request's latency; "hypothetical (scan), never observed". Owner,
  2026-10-28: "building upon hypothetical findings is a clear no-go".
- What changes: about 18 lines across 5 files, frozen into every image (`js/shell.js:19-26, :57, :112-121`,
  `js/main.js:41`, `js/app.js:94`, `scripts/_stage_website.py:27-28, :469-476, :498-499`,
  `scripts/build_firmware.py:117`), the stager's `--build-date` option and their tests. The build date stays a
  firmware build input (owner, 2026-10-05: "They must differ for being genuine").

**REG:616b** (U23) — topic tests-unit; line L4 misfit
- As taken: the mock's `DNS_LABEL_MAX` and `DNS_FALLBACK_MAX` mirrors are pinned "with four planted-mismatch bites".
- New answer: the two mirror pins stay; the four plants go.
- Basis: owner, 2026-10-23: "I never required to plant faults for every test. Planting faults is a good measure for
  complex measurement tests ... but not required for the straightforward tests ... Planting errors for those
  straightforward tests would be complete overkill." A constant-equality pin is a straightforward test. (The ruling
  came ten days after U23; at the time the record had no such rule.)
- What changes: 4 rows of `_PLANTS` in `tests_scripts/test_js_api_mirrors.py:169-175`; no product change. The same
  ruling reaches the file's other plant cases, which are not this row's.

## 3. OBS rows

| id | what it decided | the root it depends on | topic |
|---|---|---|---|
| REG:496 | split `_validate_config()` into `_validate_link()`/`_validate_receive()` for the 13-return lint ceiling | UC-8 (X): construction re-checks values buildgen already refuses; S2-G3-4: "one layer per value"; with UC-8's 22 lines gone the split's cause goes (UC-12's ring floor stays) | uart |
| REG:497 | the sender-side cap compares the declared size | UC-2 (X/H, B.md): "the peer refuses an oversize train itself (UC-1); the sender check only names the cause earlier"; not on G2's keep list | uart |
| REG:510 | `console(name, what, err=None)` fixed arity so it allocates nothing in a `MemoryError` arm | the memory-gate console lines (P4): S2-G2-3, S2-G2-4, S2-G4-6; SCAN2 section 4: "`console()` keeps one caller outside the gates, so it becomes a plain `print()`". The fact it rests on (`py/objfun.c:268-287`, fixed-arity frame vs a `*args` tuple under a locked heap) stays general knowledge | core-logging |
| REG:523 | twin Run 9 picks `NTP_NO_REPLY` or `NTP_NOT_SENT` from the host's route | NTP-4 (K, B.md): E72 split from the no-reply case; G2 families table "a send's result checked ... none: the reply wait already ends the try". The row's second half (Runs 7-8 count the persisted `WLAN_TO_HOTSPOT` warning) is a Wi-Fi expectation and stays | twin |
| REG:596b | the definitions test maps the `State` row to its `NotifyState` table; the overlay refresh's per-wake allocation left to U30 | NT-2 (H; S2-G3-8, S2-G4X-2: the `State` key and its table) and NP-5 (H with a confirmed lost-cancel defect; REPORT section 3: "revert it to the pre-audit `await ...wait()`") | led-notification |

## 4. FORM rows

| id | decision kept | the smaller form | scan row | topic |
|---|---|---|---|---|
| REG:110 | Microdot's exception print rebound from our module, `ext/microdot.py` unedited | `_print_exception()` as `report_if_fatal(exc)` plus one level-gated logger line (3-4 lines); the `MemoryError` console branch and the read-trace dedupe (`_read_traced`, the proxy's `traced` list, the ordering note at `:349`) go | S2-G2-4 (OV, P4), S2-G2-8 (the dedupe is order 2 of the rebind), S2-G4X-8 (the rebind must stay for the C-stack "ok") | webserver-rest |
| REG:527 | the same rebind, as A-2 built it at U19 (a `MemoryError` through `console()` at every level) | as REG:110; same pair | as REG:110 | webserver-rest |
| REG:529 | every dropped connection leaves one trace (WS-3, R: OR102.a (9)) | one `wrn_s` per drop path (about 6 lines against 14), without the per-connection suppression of a second entry | WS-3's minimal change (B.md); the owner's review note on `one-entry-per-fault` asks for no suppression (section 7, C11) | webserver-rest |
| REG:543 | the supervisor stops feeding one-way after the arm (OR130: "Watchdog feed: option a as recommended") | the starve flag as one value of a single reset phase integer read by comparison | S2-G1-12 ("a reset is under way" in six flags; about 10 lines fewer) | supervisor-reset-watchdog |
| REG:555b | the boot oracle's facts (`construction`, `setups`, `phases`, `fram_wired`) fixed from the model, never from the generator's text | compute it only in the test generator, not inside `generate_device()` on every image build; keep its independent rules (section 7, C10) | S2-G3-10 (X: computed by every image build, read only by the twin, tests and harness) | generated-code |
| REG:618a | a section switch lets the left section's on-wire GET finish and aborts only queued requests (keeps the owner's drop trace free of navigation noise, PICTURE M13) | never abort the on-wire GET, without `takenOver`, the second AbortController and the microtask (about 10 lines fewer) | S2-G3-15 (C of WS-3); optional NV-1 | website |
| REG:619 | the hand-over's cost accepted (median about 210 ms, 15 s cap at worst) | as REG:618a; the cost is the same | S2-G3-15 | website |
| REG:621 | the same-turn render coupling kept and pinned at the shell level | goes with REG:618a's smaller form, which no longer needs to detect the left sections | S2-G3-15 | website |

## 5. OWN rows

| id | the owner's words and source | built follows? |
|---|---|---|
| REG:107 | "We thoroughly discussed the WiFi issues and I decided everything already." and "WiFi stays valid." (owner, 2026-10-28; PICTURE section 7: a unit with no network configured returns to its hotspot after every window) | yes: an empty SSID goes to the hotspot directly |
| REG:515 | as REG:107 | yes; same decision as :107 and :582 (the skip in `_run_sta_mode()`) |
| REG:516 | as REG:107 | yes (a dead flash task restarted by the next request) |
| REG:517 | as REG:107; also a cheap bound by principle (L2: the `ticks_diff()` horizon) | yes |
| REG:582 | as REG:107; OR151's "second STA streak" reading and the unreadable-config state (owner, 2026-09-29) | yes |
| REG:583 | OR151 (2026-10-08): "The WiFi LED stays dark, even if it is activated, being completely silent in that mode. It should look like turned off."; OR49.a "FRAM writes do not count as wear"; settled 2026-10-28 | yes: LED and radio dark, one history slot per repeated warning |
| REG:585 | OR151 follow-up (2026-10-08): "add it to all layers and tiers affected, and add extensive unit tests, of all types" | yes; form note: one real-time boot of 101 s, the owner's "Test duration going up like this is anyhow something to fix - not cutting back strictness, but making it more efficient" |
| REG:587 | OR151; settled 2026-10-28 | yes |
| REG:588 | OR151; settled; for the hotspot window the owner later chose the option worded "(b) Count it like silent mode does" ("Take option b for 2", 2026-10-13, REG:624) | yes |
| REG:593 | OR152 (2026-10-08): "Any change of credentials, no matter from which side, lands in the same mode as "initial connection attempt after a fresh boot"." | yes (DEVICE_REFERENCE) |
| REG:594 | OR152, as REG:593 | yes; form note: the owner's words name credentials, the scope is the code's identity group (`SSID`, `PW`, `Country`, `Hostname`, `HotspotPW`, `buildgen/validate.py` `SETTINGS_GROUPS`), settled |
| REG:596a | Wi-Fi as REG:107 (the Wi-Fi lane's deviations: `_arm_hotspot_timer()` async, the silent entry's order, `isconnected()` first, the reused window-end path) | yes, form only |
| REG:624 | "Take option b for 2" (owner, 2026-10-13), on the question's OF-129 option "(b) Count it like silent mode does: it feeds the failure streak, then the task restart, then the budget's reboot." (the lead's wording) | yes; fact for the lead in section 7 (the premise) |
| REG:530 | review `led-request-internal-queue`: "Fine, and this for a reason: ... External commands might quickly flood it into exhaustion. The refusal and error message lets the external caller knows to try again later." | yes: "Failed" with "LED busy - retry later"; malformed is "Invalid" |
| REG:565b | review `no-gcc14-ci-leg` "ok" ("CI gets no GCC 14 build leg ... your manual two-chroot check covers it") | yes: branch 2b, the GCC 14 check stays the owner's trixie leg |
| REG:599 | owner, 2026-10-13, after asking "And the fix within this question is about the reliability of a test only on your local machine?": "Then option b is fine." | yes: fastest of three consecutive rounds, 20,000 µs unchanged |
| REG:608 | review `website-display-details`: "Fine, and maintain a reasonable number of digits per value (e.g. limit to 2 or 3 digits behind the decimal point, don't print full floats). But only for the website, the API delivers full resolution. Configured in the website config file, derived or defined from the value sourcing modules" | yes: per-field decimals from the datasheets' resolution, site default 2, the API at full resolution |
| REG:612b | OR24 (2026-09-25): "Change, don't flag, if not according. The whole repo code shall be made out of one material" | yes: one `isRecord` exported from `js/definitions.js` (`202a118`) |
| REG:613 | owner, 2026-10-13: "Actually, MPRLS and SHTC3 are not in our scope. ... that's none of the current stage's business."; the ISL29125 settings decided 2026-09-12/13/14 | yes: no open finding, no BACKLOG question |
| REG:622 | owner, 2026-10-13: "1 b", on the question's OF-111 option "(b) Refuse it ("Failed") from the command's acceptance on: one line in the status PUT handler" (the lead's wording) | yes in behaviour; the U23 flag was replaced at U30 by one reset-decided state read through the route source ("OF-111's flag gone", OF-146's row), on the owner's "1 b, 2 b" |
| REG:637a | owner, 2026-10-13: "It's okay to do some more parallel work. It went wrong when you ran 20 agents. So it's perfectly fine if you run between 4 and 6 backgrounds." "But only if it makes sense, no need to enforce a min number!" "You may also run the same amount of shell scripts in the background, so 4 to 6 agents and 4 to 6 scripts is fine." | yes: at most 6 agents and 6 heavy processes; gate rule 6 amended after the owner's "Remember the most recent decisions about parallel work" |

## 6. SUP and CHECK rows

**SUP**

| id | superseded by | does the later one stand? |
|---|---|---|
| REG:494b | owner, 2026-10-27: "Do option (c) as you recommended" (PieceBuffer's callers catch a `MemoryError` with the protocol's own fault flow); the lead's record of it: "It supersedes the "not caught" wording that came from the lead's OR143.a (2) text" | yes, the owner's; built as UC-4 (`asy_uart_comm.py:280-282, 319-321`, B.md R). Attribution gap in section 7, C1 |
| REG:500 | U35's pieces echo (`3a24c773`, 2026-10-27): the stored echo answers a GET from its pieces, no copy-out | it stands as code, but the scan classes it C (UC-5, UL-5); G2 chain 7 names a smaller form through dev's cap (section 7, C12) |
| REG:513 | owner, 2026-10-21, to "Keep timestamping once the NTP sync goes stale?": "Clock time: Option b, but with a flag in /status showing it might be stale." | yes: `UTCTime` reads `ntp_clock_valid()` and stays through a stale sync (NTP-16, SPEC A.4) |
| REG:547 | REG:622 (owner "1 b") | yes |
| REG:561 | the scanner's receiver-aware dispatch (U24 `aa3530f7`, its test at `tests_scripts/test_ticks_wrap_scan.py:370-378`) and U25's twin rewrite (`311aef80` removes `class _BoundedLog`) | yes; record note: OF-120's row still reads "open" at `11b66cd8` |
| REG:564 | the owner's 2026-10-13 parallel-work words (REG:637a) | yes; the namespace and one-run-per-worktree rules stay sound practice (CLAUDE.md's port rule). Attribution gap in section 7, C6 |
| REG:574 | the listener-close patch in the `modlwip_eagain` copy (`4de10081`, "(owner, 2026-10-26)") | yes: REPORT section 3 lists the listener close as a confirmed gap. The owner's verbatim words are not in my inputs; the commit only tags the date |
| REG:589 | REG:624 (owner "Take option b for 2") | yes |
| REG:592 | REG:599 (owner "Then option b is fine.") | yes |

**CHECK:** none. Every row was settled from source, git, the scans or the owner record. The open hardware items the
scans already list touch three rows without deciding them: NV-1 (S2-G3-15, optional, REG:618a/619/621), G2's
needs-verification 3 (the console-stall motive, REG:110/527), and OF-105 (dev's post-boot heap, REG:528's estimate).

## 7. Contradictions, facts for the lead, and counterparts

**Contradictions (13)**

| # | side A | side B | which stands |
|---|---|---|---|
| C1 | REG:494: "A-8 follows the owner's decision recorded as OR143.a (owner, 2026-10-05): the receive-site `MemoryError` catches go" | `PROJECT_AUDIT_PLAN.md:557`: the "catches go" clause is in OR143.a's integrated text (lead), not in OR143's owner words; the owner, 2026-10-27, option (c) | the owner's 2026-10-27 words; the attribution in REG:494 is a lead text labelled the owner's (L7) |
| C2 | REG:513 (`UTCTime` null after a stale sync) | owner, 2026-10-21, option (b) | the owner (SUP) |
| C3 | REG:547 ("Valid" until `quiesce()`) | REG:622, owner "1 b" | the owner (SUP) |
| C4 | REG:589 (hotspot window arm left as is) | REG:624, owner "Take option b for 2" | the owner (SUP) |
| C5 | REG:592 (spin bound as is) | REG:599, owner "Then option b is fine." | the owner (SUP) |
| C6 | REG:637 quotes the U23 lane plan: "at most three agents at once (owner, 2026-10-08)" | REG:564: the limit is "(agent, 2026-10-08)"; the owner's quoted words that day name no number ("No need to completely refrain from parallel work. Just more careful.") | the owner's 2026-10-13 words (REG:637a); the "(owner)" on the number three is a misattribution |
| C7 | REG:514's agent sentence (the resolver logs through a passed logger, UDP prints) | the pre-audit rule `SPECIFICATION.md@25caf528:1939` "Deliberately no logging — every failure surfaces to exactly one upstream owner" | the rule (DIFF REG:514). The SPEC's owner tag cites `c80d293`, which is not an object in this clone (`git cat-file` fails), so the tag's source was not checked; the rule itself is pre-audit text |
| C8 | REG:498: a transaction overlapping this end's own flash hold fails and J.5 recovers it (no byte lost); covering the hold "would force a timeout of 2,129 ms and refuse dev's 1,000 ms" | review `uart-flash-erase-overrun` "change": "this should not happen as a random side effect. Either don't lose a frame in general (preferred, if achievable with adequate effort), or halt the UART in some way for the time it takes" | the owner's words are the criterion. The ring (OR141) answers the frame loss; whether a recovered transaction on a config save counts as the "random side effect" is the owner's reading. Recorded, not decided here |
| C9 | REG:110/:527 (Microdot's print level-gated) and S2-G2-8's keep ("a 3-4 line rebind that calls `report_if_fatal(exc)` and then the plain print") | S2-G4X-7 keeps the level gate of the asyncio report because the owner turned that ungated print off | the two scans disagree on whether Microdot's print stays level-gated; the owner statements behind them pull apart (facts below). FORM keeps the gate as built |
| C10 | REG:555b: the oracle's expected facts come "from the model, never the text": "an expectation following the generator's text would prove nothing" | S2-G3-10's smaller form: the oracle reads codegen's `_setup_vars()`/`_fram_var()` "instead of copying them" | REG:555b on the rules: reading codegen's own rule functions makes the oracle check the emission only, not the order rule OR47.a (1) asks to prove ("proven for every generated device by recording the real boot sequence in the twin and asserting it"). S2-G3-10 on placement: out of `generate_device()` |
| C11 | REG:529 (A-9): "one event, one entry"; a refused head that the peer then resets logs W61 only, an arm that persisted its own entry suppresses the drop trace | review `one-entry-per-fault` "change": "It should rather stay as is, upstream layers reacting to a downstream fault may encounter following errors going above the original fault, so getting a notion of a traceback and blast radius of an error is actually desirable." | the owner's note: no suppression is asked; the newest-entry rule already folds repeats (FORM). Related: "one event, one persisted entry" is OR56.a (1), an integrated text with no quote, also behind REG:509's `_ALLOWED` table |
| C12 | REG:541: dev's `max_transfer_bytes = 12192` (the protocol default) | G2 chain 7: "With a dev cap near the echo's real need (a TOML value, G3) the chain goes (~25 lines)"; dev's own initiator sends at most 103 B | open between agent and scan: the flash-tier device scripts read the same key for their largest train (`tests_hardware/device_scripts/uart_crossover_exchange.py:1, :140`), so a smaller cap also shortens the bench's largest-train proof. Value question for the cleanup plan; wire format untouched either way |
| C13 | REG:616b's four planted-mismatch tests (2026-10-13) | owner, 2026-10-23: "Planting errors for those straightforward tests would be complete overkill." | the owner (DIFF REG:616b) |

Picture-line misfits (the DIFF rows): REG:511, :519, :531, :615b (L2); REG:514 (L3); REG:520b (L1); REG:616b (L4).

**Facts for the lead (owner statements or records that pull apart; no question framed)**
- Console at DebugLevel 0. OR35.a (2026-09-26): "Console logs actually should keep printing all. Thereby, the short,
  limited error logs are protected, while the console carries the whole unfiltered truth." That answer was given to
  OR35, log flooding by repeats. The owner on the asyncio report: "Yes, build it that way." (2026-10-07, SPEC F.1: "from
  DebugLevel 1 one line and the traceback, nothing at 0"), confirmed by Q6 "Option a" (2026-10-26), and "Keep as is,
  no added complexity." (2026-10-21) on counting silent deaths. The logger's console output was level-gated before the
  audit. REG:110/527 and S2-G2-8 vs S2-G4X-7 meet here.
- Two "1 b" answers on 2026-10-13: REG:622 cites "1 b" on the in-session list (1. OF-111, 2. OF-129); the OF-145 and
  OF-146 rows cite "1 b, 2 b" answering the U23 report's questions 1 and 2. Both are dated the same day; the records
  keep them apart, and REG:625's two questions were answered (b) by the second.
- REG:624: the owner chose (b) on the premise "the window timer continously fails, the Hotspot never ends"; REPORT
  section 3 lists "alarm-pool exhaustion in normal operation" as refuted and S2-G2-1 classes the refused-arm family H.
  Wi-Fi is settled (2026-10-28), so this stays a fact.
- REG:108/:518 with REG:513: after an NTP settings change, `UTCTime` is null until the next sync (the option (b) text)
  while `LocalTime`, `UnixTime` and the sensor TS keep the old clock (REG:518, agent). Each step is owner-decided or
  consistent with it; S2-G4-15 and SCAN2 section 9: "Conservative: unchanged."
- OF-120 reads "open" at `11b66cd8` although U24 fixed the scanner's receiver dispatch (`aa3530f7`) and U25 removed
  the twin class it misread (REG:561).
- REG:574's owner basis is a date tag in a commit message (`4de10081`); the verbatim words were not found in my inputs.

**Within the set, consistent groups (no contradiction):** REG:107/:515/:582 (empty SSID); :547/:622/:623/:625
(`ResetErrors` around a command); :589/:624 and :592/:599 (owner answers closing agent holds); :110/:527 (one
decision, two rows); :618a/:619/:621 (the hand-over); :595/:600 (Part N citations); :108/:513/:518 (the clock).

**Likely counterparts in other sets**
- REG:511 ↔ REG:112 (U16: `LOG_RAM_ONLY` for a store that cannot use FRAM) and REG:487 (U16: the allocator's refusal).
- REG:510, :514 ↔ REG:730 (U30: the UART layer's caught allocation failures print through `console()`).
- REG:110, :527 ↔ REG:741 (U30 F1b: "the rebound `_print_exception()` reports first") and review `c-stack-reboot`.
- REG:547, :622, :623, :625 ↔ REG:737 (U30 F1a: `ResetErrors` refused whole while a refusal predicate holds) and
  REG:744 (overlapping `ResetErrors`).
- REG:615b ↔ REG:794 (U35 close: OF-144 closed by `1b638f1`, `7d6d255`) and REG:681 (U27 close).
- REG:108, :513, :518 ↔ REG:783 and REG:795 (U33/U35: the owner's clock answer and `TimeStale`'s form).
- REG:574 ↔ REG:727 (U30 close moving OF-122).
- REG:500, :541 ↔ the U35 PieceBuffer rows (the owner's option (c), 2026-10-27) and review `go-ahead` (OR143).
- REG:498, :541 ↔ review `uart-flash-erase-overrun`.
- REG:529, :531 ↔ reviews `http-head-limits`, `status-fields-added-and-left-out`, `one-entry-per-fault`.
- REG:530 ↔ review `led-request-internal-queue`; REG:608 ↔ `website-display-details`; REG:565b ↔ `no-gcc14-ci-leg`;
  REG:569 ↔ `bench-sudo-checked`; REG:580 ↔ `bench-psk-fallback`; REG:542, :546 ↔ `system-command-sequence-details`;
  REG:519 ↔ `dns-fallback-setting` and the routine `ntp-malformed-text`; REG:523 ↔ the routine `new-dns-ntp-errnos`.
- REG:616b ↔ the planted-fault rows of other units (the U35 planted-fault campaign; REG:377 at U13 and similar).
- REG:564, :637 ↔ the concurrency rows of other units.
- REG:561 ↔ the U24/U25 rows on OF-120.

## 8. SAME rows

**The umbrella rows** (REG:494a, :509, :526, :540, :565a, :584, :598): the adoption of each lane plan's section-5
defaults on the owner's behalf is the process OR2.c set ("yes, that matches") and OR145's go-ahead let run; each row
is in the owner-review list, labelled agent, as L7 asks. SAME covers that process only. Each row's reasoning, "the more
conservative option each time", was read as the safer behaviour, which DRIFT 2.5 shows was read the wrong way (L7:
the smallest, most reversible change); the owner agreed with "Every finding became code ... It should have gone in
as knowledge, a test, or a question to the owner" ("I agree with wour conclusions about scope and effort.",
REPORT). The content behind the defaults is judged per mechanism by the scan rows, not here: for U17 UC-2, UC-6, UC-8
and D-H12/H14 (A.U17.21); for U18 the resolver widening (S2-G2-5), NTP-3/DNS-1 (S2-G2-6), NTP-4; for U19 WS-2, WS-5,
WS-7, WS-9, WS-11; for U20 the build checks D-H13 to H23 (S2-G3-1 to -3) and the oracle (S2-G3-10); for U23 the
browser validator's per-hint growth (S2-G3-13).

U17
- REG:494a — uart — U17 defaults as process; wire format untouched, A14/A15/A16 recorded as Class A (note only).
- REG:495 — tests-unit — the cancel sweep stays in one file, under the per-file limit.
- REG:498 — uart — no timeout widening for the flash hold; J.5 recovers (C8 for the owner's criterion).
- REG:499 — uart — a valid-CRC frame of the wrong length counts toward the mismatch diagnostic: the dead-but-busy
  link the owner's out-of-band parameter rule diagnoses (UC-9, R); Python-internal, no byte changed.
- REG:501 — tests-unit — a sweep step is one sleep, not a scheduler turn: host-speed independent, about 2,500 builds
  fewer per check.
- REG:502 — twin — the pause test reads the patched clock; dev's own parameters, no literals.
- REG:503 — docs-records — changelog rows by first-landing commit; the exerciser is not the protocol module.
- REG:504 — docs-records — changelog text names only what is on the tree.
- REG:505 — ci-tooling — `ParamSpec` on `_call()`, annotations only.
- REG:506 — docs-records — J.5 follows the DMA path's receive-error clear.
- REG:507 — tests-unit — two sleep tunables leave; tests ordered by events.
- REG:508 — memory-gc — `pieces()` yields the pieces; no memoryview per iteration.

U18
- REG:108 — ntp-dns — LED alerts gate on "clock set" (NTP-18, C of NTP-11 R), consistent with the owner's later
  option (b) (2026-10-21).
- REG:509 — process — defaults adopted; the `_ALLOWED` table follows the code; two owner questions went to BACKLOG
  and were answered (OR150).
- REG:512 — timing-waits — new constants in seconds; one ms conversion in one unit (U31).
- REG:518 — ntp-dns — a forced resync clears `Synced`/`LastSyncAge` (OR102 "3. a"), `LocalTime` keeps (S2-G4-15).
- REG:520a — ntp-dns — one yield per received datagram: confirmed gap (CD-6, REPORT section 3).
- REG:521 — website — the put matrix's `ipv4List` value; titles unchanged.
- REG:522 — docs-records — docs written to the merged tree.
- REG:524 — docs-records — sentences written in the unit that makes them true.
- REG:525 — tests-unit — a 5 s bound that ends a lock-wait regression instead of hanging the file (the hang rule).

U19
- REG:526 — process — defaults adopted; the two system words land with their handlers at U20.
- REG:528 — memory-gc — a serving-demand budget that can fail (the plan's default took the whole GC heap and could
  never fail; OR33.a "can never fail ... drop"); its post-boot measurement stays owed (OF-105).
- REG:532 — error-catalog — W48 keeps its number and meaning; free. Its stated reason (FRAM history across reflashes)
  is not required (OR47.a), so it is no reason to keep the never-reuse rule (S2-G4X-6).
- REG:533 — website — the mock's injected-failure change staged with its mirror unit.
- REG:534 — website — the mock answers like the server in the same merge (Part G mirror).
- REG:535 — driver-scd30 — an unreadable SCD30 file store answers the base unavailable marker (A-B8, kept by
  S2-G4-17), as every module's store does.
- REG:536 — buildgen-toml — every output built before any is written: no stale mix, no traceback (OR23 "the build
  always aborts on errors and reports them such that a user can easily see what to do"; D-H2).
- REG:537 — generated-code — the API reference lists what GET and PUT carry (D-H7, R).
- REG:538 — docs-records — SPEC states the U19 firmware, not U21's override.
- REG:539 — docs-records — end-state comments at their three sites.

U20
- REG:540 — process — defaults adopted; three lane merges (fewer lanes, toward OR107; twelve lanes is still the scale
  PICTURE M9 names).
- REG:541 — uart — dev's `rx_ring = 512` keeps the heap (OR141 "keep a strict eye on how that integrates with the heap
  allocation and fragmentation"); the cap at the protocol default (C12).
- REG:542 — supervisor-reset-watchdog — a system command over REST is proven not to deadlock on the owner lock,
  through the real PUT path (review `system-command-sequence-details`: "only make sure it's working watertight").
- REG:544 — tests-unit — renames wait for U25.
- REG:545 — config — one unavailable answer for an unreadable store in every module; `ConfigFaults` names it (OR138:
  "Unreadable or damaged files should be visible in some status field").
- REG:546 — supervisor-reset-watchdog — record 9 is part of the owner's reset record (A-S1, OR60); the shutdown's
  report of an unpersisted store is on SCAN2's must-stay list.
- REG:548 — website — a list of scalars renders as text.
- REG:549 — ci-tooling — one stub-gap ignore in `src/` with its removal trigger; net fewer ignores.
- REG:550 — website — the mock's `MemFree` from SPEC I.6.
- REG:551 — error-catalog — page text true at U20; boot-phase rows per OR102.a (6).
- REG:552 — buildgen-toml — a schema value with no JSON form is a BuildError, not a traceback (OR23).
- REG:553 — buildgen-toml — malformed tags are BuildErrors (OR23; D-H29 R).
- REG:554 — buildgen-toml — source facts cached by text (D-H5, measured: 72 s to 9 s).
- REG:555a — buildgen-toml — an unwritable output directory is a BuildError.
- REG:556 — generated-code — the existing stripper, unchanged.
- REG:557 — buildgen-toml — FRAM is optional (OR89.a); `bus.boot-clear-budget` is the one I2C timing check that
  stays (S2-G3-1 keeps the budget, the ceiling goes); one rule for an absent or untyped int.
- REG:558 — tests-hardware — the device script's dead counting loop goes; hand feeds where no supervisor runs.
- REG:559 — generated-code — the no-autostart image's one REPL line (OR86).
- REG:560 — twin — one tagged watchdog copy, a bounded deque, production start order.
- REG:562 — tests-unit — the mock boot stops its fake timers; one FRAM array per process.
- REG:563 — twin — the SCD30 fake per the datasheet's offset note.

U21
- REG:565a — ci-tooling — defaults adopted; the apt split only after proof; one offline upgrade of the shared
  toolchain by the lead.
- REG:566 — process — lanes on private toolchain copies after the rebuild-under-reader incident (OF-126).
- REG:567 — ci-tooling — the unread man-page text left to the owner's chroot and installer leg.
- REG:568 — ci-tooling — `sudo` in the caller's session, every other command in its own; host tooling, low.
- REG:569 — ci-tooling — `sudo -k -n` probe (review `bench-sudo-checked` "ok": check, never write).
- REG:570 — ci-tooling — no stale toolchain record after an interrupted setup.
- REG:571 — ci-tooling — host-lwIP-only flags; rp2 builds unchanged.
- REG:572 — ci-tooling — member order only on files rewritten whole (the owner's later "Option d is fine").
- REG:573 — tests-unit — the EAGAIN hammer avoids the listener-close trip and counts GC-paused rounds.
- REG:575 — release — the tick test image only in its own build dir; a release name refuses it (OR139's image).
- REG:576 — ci-tooling — the readback proven by real builds, not by fakes that follow their own text.
- REG:577 — ci-tooling — no command line before its runner exists.
- REG:578 — docs-records — "not yet re-checked on a GCC >= 14 host".
- REG:579 — docs-records — the picotool version rule from pico-sdk.
- REG:580 — docs-records — owner tags with their quotes (OR114, OR139, OR140.a (1)); no credential value written.
- REG:581 — docs-records — README's test timing.

U22
- REG:584 — process — operational rulings (disjoint lanes, namespaces, lead-only rebuilds), within the owner's
  2026-10-08 "Just more careful."
- REG:586 — twin — the two `LEDWifiOn` settings checked in two stages of one boot.
- REG:590 — twin — the device picked from the plans; all six devices wire a NeoPixel and a FRAM (one instance each in
  every `devices/*.toml`), so the pick is the first device, the pattern the owner allowed on 2026-10-23 ("the first
  device runs specific tests, which are always and guaranteed present").
- REG:591 — tests-hardware — the bench names its device once (OR78.a "the hardware tier's fixed `dev`").
- REG:595 — docs-records — Part N citations moved to on-branch commits.
- REG:596c — twin — the twin knob, a third `_Rp2Gmtime` copy for U24 to fold, A.4's clause kept.
- REG:597 — process — the pre-gate check runs the whole tier; check scripts use the eight scopes (no `arduino/`).

U23
- REG:598 — process — defaults and operational rulings adopted; A-11 then answered by the owner ("1 b").
- REG:600 — docs-records — no lane hash in Part N.
- REG:601 — tests-unit — lead edits outside lane sets; allow-lists shrink; one contract row per new rule id (OR23).
- REG:602 — website — the JS mirror pinned to `src/` by `ast` (Part G).
- REG:603 — website — the mock's deviations, each failing visibly where the old form passed.
- REG:604 — website — stager checks fail the build, not the page; styles only for new owner-asked states, no change
  to the existing look (OR94).
- REG:605 — website — the module order derived, not hand-listed.
- REG:606 — buildgen-toml — three rule ids for the owner-asked tags (OR100 "20 c", `website-display-details`).
- REG:607 — webserver-rest — a raising reset logged once under E14, no new code.
- REG:609 — tests-unit — test efficiency; no member-order sweep outside `src/` (the owner's "Option d").
- REG:610 — website — details of the owner-approved codes, ages and accessibility.
- REG:611 — website — the Clear/Apply in-flight rule and the declined-dialog text (the owner's dialogs, OR140.a (3)).
- REG:612a — website — OF-143 recorded as a finding, not coded.
- REG:612c — website — a non-object GET body takes the existing failure banner (one condition, `js/render.js:619`);
  REPORT section 6.4 lists the banner without agreement, but it adds no path of its own.
- REG:614 — website — poll and shell robustness of the owner-approved unattended page.
- REG:615a — website — no extra reload after a failed first watch (unrequested behaviour).
- REG:616a — website — selector escape, one render-wait tunable, shared `isRecord`, H.5 citations.
- REG:617 — website — live-tier details; the LED's second-command refusal confirmed by curl.
- REG:618b — website — counts printed on every run (no evidence lost); the put matrix's split; OF-147 routed.
- REG:620 — website — reduced motion in the live matrix, about a third less wall clock per shard, identical counts (OR39).
- REG:623 — supervisor-reset-watchdog — a reset begun before acceptance completes and answers truthfully.
- REG:625 — supervisor-reset-watchdog — OF-145 and OF-146 put to the owner (answered "1 b, 2 b").
- REG:626 — ci-tooling — ESLint ceilings at the measured maxima.
- REG:627 — process — a waiting lane sees only a finished base.
- REG:628 — docs-records — docs state the tree; no wrong dates.
- REG:629 — docs-records — the docs rulings: "owner-reviewed" only where a review record exists; no lane hash.
- REG:630 — docs-records — the build-environment entry; runnable lines.
- REG:631 — docs-records — no claim of a Run 13 that does not exist.
- REG:632 — docs-records — comments corrected outside lane sets.
- REG:633 — docs-records — H.3 states what a poll repaints.
- REG:634 — docs-records — "by design" with no decider reworded with the source's reason.
- REG:635 — docs-records — the current effect stated while OF-145 was open (changed at U30 after the owner's answer).
- REG:637b — process — doc checks after `git add`; record times from git, not estimates.
- REG:649 — website — the reload check waits for the twin's documented drain and names the open requests.

**Fact:** REG:636 (U23, process) — the docs merge record (`e14d76f`, the final head `659c22c`); no decision.
