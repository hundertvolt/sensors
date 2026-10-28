# History trace: owner paragraphs dropped by the 2026-07-30 merges

Audit file (M.PROC.006, from A.U0.15; unit U0, step (7)). Register row: G9/R33. Removed with `audit/` at phase D.

## Method

- **Merges**: `f455d34` (captive-dns branch), `8d89ff5` (async-connect branch), `7a7f4b6` (uart-driver branch),
  merged one after another on 2026-07-30 into `claude/merge-four-branches-g0ohsq`. All three share the merge base
  `19a8b3b`. Every owner-vocabulary line they drop is in BACKLOG.md. Every text file that differs between the two
  parents was checked, both sides, legacy/`arduino/`/`ext/` excluded, and no other file loses one.
- **Dropped line**: added by `<merge>^2` relative to the merge base (`git diff -U0 <base> <merge>^2 -- BACKLOG.md`),
  absent from `<merge>:BACKLOG.md`, and not added by `<merge>^1`. Blank lines are ignored. A per-line multiset
  version of the same rule gives the same owner lines.
- **Paragraph**: one markdown block of `<merge>^2:BACKLOG.md`. A heading, a blank line or a list marker (`-`, `*`,
  `N.`, at any indent) starts a new block, so each nested bullet is its own paragraph.
- **Owner filter**: a paragraph counts if one of its dropped lines matches `owner`, case-insensitive. This covers
  "owner", "owner-requested", "owner-confirmed", "Owner direction" and also "Owner-directed" and "Owner asked".
- **Evidence** is cited at the audit-branch HEAD `46ba217`. Outside `audit/`, HEAD equals the audit baseline
  `798e5a7` except for two places: README.md:700-708, and SPECIFICATION.md:337-364, after which SPECIFICATION.md
  lines sit +5 relative to `798e5a7`.
- The derivation scripts are host-side Python run against git plumbing (`git rev-parse`, `git merge-base`,
  `git diff -U0`, `git show`). They live in the session scratchpad (`trace/derive.py`, `paras.py`,
  `s01_recon.py`), not in the repo.

## Counts and how they reconcile

| merge | lines dropped from `^2` | owner lines (the 60 quick count) | owner paragraphs (traced below) |
|---|---|---|---|
| `f455d34` | 302 | 11 | 10 |
| `8d89ff5` | 1,145 | 42 | 33 |
| `7a7f4b6` | 327 | 7 | 6 |
| **total** | 1,774 | **60** | **49** |

- **60 lines** reproduce A.U0.15's quick count exactly (11/42/7). Grouped into paragraphs they make **49**. A
  case-sensitive whole-word filter on the four listed words gives 55 lines and 44 paragraphs; the difference is
  four "Owner-directed" lines and one "Owner asked" line.
- **The 78 is reproduced, but it is not a count over the three merges.** S01's RP03 (a) rule takes lines "added by
  one parent" (both sides), across all text files, and was applied to the four large-loss merges
  (`audit/refined/S01.md:58`: "3,127 in e5d2c43/8d89ff5/7a7f4b6/f455d34"). Under that rule:
  - `f455d34` gives 11 paragraphs: the 10 above plus one first-parent paragraph (R01 below).
  - `8d89ff5` gives 33; `7a7f4b6` gives 6.
  - `e5d2c43` (the 2026-09 merge of `main` into the build-chain branch) gives 28 more.
  - 11 + 33 + 6 + 28 = **78**, exactly.
  - S01:48 and G9/R33 attribute all 78 to the three 2026-07-30 merges, and that attribution is the error.
  - The dropped-line total under this rule is 3,456, not 3,127. The 329-line gap is in the file filter (non-owner
    lines), not in the owner paragraphs.
- **Paragraph-rule sensitivity**:
  - Counting a paragraph whose owner word sits on a *kept* line adds one paragraph: `8d89ff5^2:BACKLOG.md:3055-3076`,
    open question 13 (`write_config()` long-block coordination). Its outcome is resolved: BACKLOG.md:167-172 #4,
    "Decided".
  - Grouping by blank line alone, without list items, collapses `8d89ff5`'s nested BACKLOG to 3 paragraphs.
- **Coverage**: all 78 get an outcome here. The 49 second-parent paragraphs of the three merges are in the main
  table. The 29 others (R01, and R02-R29 for `e5d2c43`) are in the reconciliation appendix, which is outside
  M.PROC.006's scope and traced less deeply.

**Outcomes (49)**:

| outcome | count | rows |
|---|---|---|
| stands | 5 | HT.08, HT.19, HT.22, HT.27, HT.31 |
| resolved/migrated | 16 | HT.11, HT.13, HT.15, HT.16, HT.18, HT.23, HT.25, HT.26, HT.28, HT.33-HT.35, HT.37, HT.38, HT.42, HT.43 |
| pruned as history | 15 | HT.01, HT.03, HT.05, HT.06, HT.10, HT.14, HT.17, HT.20, HT.21, HT.24, HT.30, HT.32, HT.45, HT.48, HT.49 |
| lost | 8 | HT.07, HT.09, HT.12, HT.29, HT.39-HT.41, HT.47 |
| drifted | 5 | HT.02, HT.04, HT.36, HT.44, HT.46 |

Every lost row has a register home.

Outcome vocabulary (G9/R33):
- **stands**: the decision holds at HEAD with the same meaning, in text or in code. A code-only decision needs no
  tag (H2's rule).
- **resolved/migrated**: the open point was done or answered, or its content moved to the named home.
- **pruned as history**: a work request, pass header, one-time exception or overtaken shape, with no forward rule.
- **lost**: a standing owner rule with no statement at HEAD (the code may still conform).
- **drifted**: stated at HEAD, but the actor, reason or scope changed.

Each row gives the trail, the commit on the side branch that introduced the owner line (`git log -S`).

## Main table: the 49 paragraphs

| id | merge | site (owner line) | trail | quote | outcome | evidence at HEAD | register home |
|---|---|---|---|---|---|---|---|
| HT.01 | f455d34 | `f455d34^2:BACKLOG.md:1868-1880` (:1879) | `639e992` | "Kept the existing `debug: bool` + `print()` shape … the owner's own framing for this pass ("without adding too much complexity") doesn't favor the heavier mechanism" | pruned as history (overtaken) | `src/captive_dns.py:15, :63` use `make_logger()`/`PrintLogHistory` (`DNSSRV`), per the owner's 2026-08-07 decision `74cfa7f` (SPEC:1894-1897, H1.02). The complexity framing is stated nowhere | G6/R24 (G9/R33 routing); overtaking decision G9/R27 (H1.02) |
| HT.02 | f455d34 | `f455d34^2:BACKLOG.md:1882-1894` (:1882) | `639e992` | "**Test approach, owner-directed real-vs-fake split** … A `_FakeUDPS` stand-in" | drifted (actor) | Instance stands (`tests/test_captive_dns.py:331-337`). The rule "mock only what cannot be produced for real" has no owner source at SPEC E.4 | G2/R05 Rank (H.01) |
| HT.03 | f455d34 | `f455d34^2:BACKLOG.md:1909-1918` (:1909) | `639e992` | "(owner-authorized "quick mechanical fix" for out-of-scope drift surfacing in CI): two stale `# type: ignore` comments" | pruned as history | One-time authorization. Tool pins and `warn_unused_ignores` govern this now (CLAUDE.md "Code quality tooling") | none needed |
| HT.04 | f455d34 | `f455d34^2:BACKLOG.md:1922-1926` (:1922) | `96ba194` | "Owner-directed follow-up … mocking only what genuinely can't be produced for real." | drifted (actor) | Same rule as HT.02, agent-ranked at SPEC E.4 | G2/R05 Rank (H.01, B081) |
| HT.05 | f455d34 | `f455d34^2:BACKLOG.md:1928-1929` (:1929) | `96ba194` | "the "either by itself or by a called function" shape the owner asked to re-check" | pruned as history | Pass header (pass 4 H.17, B080); the fixes are in code | none |
| HT.06 | f455d34 | `f455d34^2:BACKLOG.md:2006-2010` (:2006) | `d92da47` | "Owner-directed follow-up: re-audit the whole file once more for oversights" | pruned as history | Pass header (H.17, B130) | none |
| HT.07 | f455d34 | `f455d34^2:BACKLOG.md:2083-2097` (:2083) | `881c5f8` | "every one just means "this input isn't usable, fall back." Collapsed all four to plain `except Exception:`" | lost (rule; code holds) | `src/captive_dns.py:105, :187` keep `except Exception:`. No doc states the owner's untrusted-input rule (pass 4 H.06 LOST) | G5/R16 Req + Sources (H.06); G6/R24 (G9/R33) |
| HT.08 | f455d34 | `f455d34^2:BACKLOG.md:2104-2111` (:2106, :2110) | `06e5885` | "the project owner's concern that hardening shouldn't drift the file away from actually-working, everyday behavior … owner-authorized fixes" | stands | Subnet filter and malformed guard at `src/captive_dns.py:85-109, :167-187` (H.16, B069/B091). The legacy-parity concern is carried by OR12.a | G9/R04 |
| HT.09 | f455d34 | `f455d34^2:BACKLOG.md:2113-2128` (:2124) | `06e5885` | "consistent with the project owner's "general containment, not per-condition" direction" | lost (rule; fix holds) | The fix is at `src/captive_dns.py:180-185` (`question_end > len(data)`). The direction is stated nowhere | G5/R16 Sources (H.06, B092) |
| HT.10 | f455d34 | `f455d34^2:BACKLOG.md:2145-2151` (:2145) | `2a64a43` | "Owner-directed pass applying section 11's "3 lines, prefer fewer" per-comment limit" | pruned as history | The rule stands at CLAUDE.md:412-420 (H.17, B161) | none |
| HT.11 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:112-136` (:128, :132) | `caf4f7f` | "(owner-reported field case: router up, upstream internet down) … an architecture decision flagged to the owner for discussion" | resolved/migrated | `getaddrinfo()` was replaced by `src/asy_dns_client.py` (SPEC F.3:3664-3665); the "can't be timeout-wrapped" fact is at SPEC F.2:3608. The field case is tested at `tests/test_ntp_wifi_dns_integration.py:364, :427` and on the bench ("WiFi available but no internet", `tests_hardware/README.md:772, :796`) | G6/R34; C04 (G9/R36) retires the `getaddrinfo()` half |
| HT.12 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:137-145` (:137) | `cc911be` | "**Standing decision (owner-confirmed): adopt a genuine non-blocking alternative to `getaddrinfo()` (or any other currently-unavoidable blocking call) as soon as one reliably exists**" | lost | "non-blocking alternative" has 0 hits in CLAUDE.md, SPECIFICATION.md and BACKLOG.md. CLAUDE.md:193-196 says the opposite ("settled, don't re-propose") | G9/R36 C04 (OR89.a (4)) → A.U0.22 |
| HT.13 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:146-166` (:146) | `cc911be` | "Second full exception/blocking audit of `asy_ntp_client.py` (owner-requested …) found three real gaps" | resolved (code) | `src/asy_ntp_client.py:146-147` (mktime/gmtime guarded), `:215-217` (`network_available()` guarded), `:287, :337` (`Timer.init` catches) | none |
| HT.14 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:219-221` (:219) | `ce6d402` | "Third pass (owner-requested "go through it again")" | pruned as history | Pass header (H.17, B148) | none |
| HT.15 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:248-264` (:249) | `c7b9431` | "since fixed (owner-requested): NTP's 32-bit "seconds since 1900" field wraps in 2036" | resolved (code) | `src/asy_ntp_client.py:48-53, :253-255` | none |
| HT.16 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:300-347` (:300, :307) | `208e003` | "Fourth pass (owner-requested: re-validate the era-rollover fix …) … one genuine new gap, since fixed (owner-requested)" | resolved (code) | Leap Indicator and stratum rejection at `src/asy_ntp_client.py:55-57, :245-250` | none |
| HT.17 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:348-375` (:349) | `c7b9431` | "(`api_helpers.py`), since fixed (owner-requested, overriding this file's normal out-of-editing-scope caution for this one fix)" | pruned as history | `api_helpers.py` deleted (`342c610`; `src/api_response.py:2`). One-time exception (H.17, B142/B147) | none |
| HT.18 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:376-392` (:376, :381) | `ee6bae4` | "Fifth pass (owner-requested): migrated `asy_ntp_client.py`'s configuration management … the exact "legacy style" pattern the owner pointed at" | resolved (code) | `src/asy_ntp_client.py:95` `class AsyNtpClient(SensorReaderConfig)` | none |
| HT.19 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:393-403` (:393, :395, :402) | `ee6bae4` | "the owner explicitly chose the full quartet over a config-only subset … "missing setters... not in scope here, they will be added later on globally"" | stands | The getter quartet is at `src/asy_ntp_client.py:363-374`. The setters arrived globally (`handle_set_cmd`, `src/api_response.py:85-96`) | none (code-only) |
| HT.20 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:468-504` (:468) | `61d2a59` | "owner-requested: "add extensive tests for the newly introduced methods, including edge cases"" | pruned as history | Work request (H.17, B141) | none |
| HT.21 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:505-508` (:505) | `54c0d42` | "(owner-requested, same "no uncaught exceptions, no blocking/hangs except the one permitted `getaddrinfo()` call" bar" | pruned as history | Pass header (H.17, B151). The no-blocking bar stands at CLAUDE.md:210-212 and SPEC F.3; its `getaddrinfo()` exception is gone | none |
| HT.22 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:528-541` (:539) | `54c0d42` | "the owner's current, broader "no blocking/hangs are allowed" instruction supersedes that earlier deferral" | stands | Bounded wait at `src/asy_wifi_service.py:110, :339, :348` (`errno=18`); the principle is at CLAUDE.md:210-212 | none |
| HT.23 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:560-574` (:571) | `54c0d42` | "flagged for the owner to decide whether `wlan.config(reconnects=0)` … is wanted" | resolved | Restored as BACKLOG #9 by `3383dee` (2026-07-30) and closed by `8784c66` the same day ("no such config param exists on the CYW43/rp2 port", an agent claim not re-verified here). HEAD handles the codes (`src/asy_wifi_service.py:607-610`), and BACKLOG.md:293-300 (#29) records `STAT_WRONG_PASSWORD` surfacing on hardware | none |
| HT.24 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:589-594` (:589) | `fd65a52` | "Second full re-audit pass (owner-requested again, same bar)" | pruned as history | Pass header (H.17, B159) | none |
| HT.25 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:671-681` (:671, :678) | `b257b0c` | "Three real, load-bearing findings, worth the project owner's attention" | resolved | The owner decided them (HT.27, `dd22d43`); now SPEC A.4:269-275 | G6/R25, G3/R61 (A13) |
| HT.26 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:709-731` (:728) | `b257b0c` | "Worth the owner explicitly re-confirming this trade-off" | resolved | Confirmed intentional (HT.27). SPEC A.4:271-273: "permanent WiFi deactivation after a second STA failure streak … only a physical power-cycle clears it" | G6/R25, G3/R61 (A13) |
| HT.27 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:769-772` (:769, :770) | `dd22d43` | "The project owner confirmed directly, for both findings, that they're intentional design choices rather than gaps" | stands (migrated) | SPEC A.4:269-275 "Functional behaviors confirmed intentional by the project owner" (B157/B158 → DP `dd22d43`, A13) | G3/R61, G6/R25 |
| HT.28 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:780-793` (:781) | `8696c1d` | "the project owner confirmed the state-machine rework is already underway" | resolved (code) | `src/asy_wifi_service.py:119-126, :182` (`_conn_phase`, `_PHASE_*`) | none |
| HT.29 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:794-804` (:799) | `dd22d43` | "The project owner rejected that trade-off directly: keep the file's own coding style consistent, adapt the test to the code rather than the code to the test." | lost (rule; instance holds) | Instance: `src/asy_wifi_service.py:122-126` `const()`, mirrored at `tests/test_asy_wifi_service.py:14-17`. The rule is in no doc | G2/R16 Rank (RF015); doc restoration in U36 (`audit/actions/U36a.md:441-450`) |
| HT.30 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:831-834` (:831) | `3313be2` | "(owner-requested: "go through our recipe paragraph by paragraph")" | pruned as history | Pass header (H.17, B150) | none |
| HT.31 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:844-866` (:861) | `d725042` | "**The project owner then explicitly directed the fix** ("adapt the schema to fit the actual value") - `_VAL_HOST`'s max is now 32" | stands (code; owner words gone) | `src/asy_wifi_service.py:48` `("Hostname", "str", "SensorNode", 1, 32, None)`. The REST-route 1-63 it flagged went with `sensortask-wozi.py` | G6/R28 (G9/R33 routing) |
| HT.32 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:867-877` (:874) | `d725042` | "**Project owner confirmed this is expected to resolve on its own once the two branches are merged together**" | pruned as history | `DRIVER_SPEC.md` was merged, then folded into SPEC and deleted (README.md:677) | none |
| HT.33 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:894-898` (:896) | `a6abe13` | "(owner-requested: replace `getaddrinfo()`, inspired by but not copied from `github.com/vshymanskyy/aiodns`, then reassess whether the shared lock is still needed)" | resolved | `src/asy_dns_client.py` exists; the lock is retired (SPEC F.3:3664) | none |
| HT.34 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:911-922` (:912) | `a6abe13` | "per the owner's explicit "question if it is correct" instruction" | resolved (code) | `src/asy_dns_client.py:41-53` (exact-size query), `:74-76` (QR and RCODE checks) | none |
| HT.35 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:923-938` (:923) | `1da7886` | "A third real correctness gap found in a follow-up owner-requested review pass" | resolved (code) | `src/asy_dns_client.py:30, :82-83` (top-two-bits mask) | none |
| HT.36 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:939-944` (:942) | `a6abe13` | "Matches the owner's explicit "limitations are acceptable as long as it works fine in most cases"" | drifted (owner source lost) | The limitation is stated without an actor at `src/asy_dns_client.py:5-7, :70, :85` | G6/R34 Rank (RF013) |
| HT.37 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:954-971` (:954) | `a6abe13` | "Long-block lock removal, verified thoroughly before removing anything (owner's explicit condition)" | resolved | SPEC F.3:3660-3665 (retired). The `write_config()` question it left open is BACKLOG.md:167-172 #4, decided | none |
| HT.38 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:1011-1034` (:1011) | `f4ae8a8` | "A follow-up owner-requested review of all three files together" | resolved (code) | `src/asy_ntp_client.py:150-157, :431-432` (`_safe_get_dns_server()`) | none |
| HT.39 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:1084-1091` (:1084, :1085, :1089) | `5ddbcd3` | ""define the timeouts per service and compute dependent/summable timings... Only the individual timeouts need to be set as parameter" … "keep it simple... all computation is done centrally"" | lost (rule; code conforms) | Values at `buildgen/codegen.py:19-21`, forwarded verbatim (`:346-348, :413`). "per service" and "summable" have 0 hits in the docs, `src/` and `buildgen/` | G4/R54 Req + Rank (RF014) → U8 |
| HT.40 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:1096-1101` (:1100) | `5ddbcd3` | "the owner's second round of feedback ruled that out — they're just plain values this class trusts were set correctly at construction" | lost (rule; code conforms) | Plain constructor parameters, tested at `tests/test_asy_ntp_client.py:800, :885` | G4/R54 |
| HT.41 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:1110-1115` (:1112) | `5ddbcd3` | "`sensortask-wozi.py` is the one place these three leaf values are actually decided … "just a few lines," per the owner's own framing" | lost (rule; the place migrated) | The one place is now `buildgen/codegen.py:19-21` | G4/R54 |
| HT.42 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:2796-2807` (:2803) | `90171f8` | "Resolving it needs an owner decision, not a guess: promote `captive_dns.py` too …" | resolved | `src/captive_dns.py` promoted; `asy_wifi_service.py` promoted in `c4fb625` | none |
| HT.43 | 8d89ff5 | `8d89ff5^2:BACKLOG.md:3080-3089` (:3085; :3082 kept by the merge) | `7bd9748` | "(owner's own framing: "note that we will rename it later in another context")" | resolved | Renamed `max_module_error` by `27ae6c6` (2026-08-11): `src/base_classes.py:155, :263`. `max_i2c_err` has 0 hits in `src/` | G9/R33 (RF018) |
| HT.44 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:1840-1844` (:1840) | `645fe10` | "**Embedded, non-standard `CRC16` swapped for `crc_checks.py`'s `CRC_Base` family** (owner decision)" | drifted | `UART_C_PORT_CHANGELOG.md:61` (A7) says "Not a deliberate change"; the swap was deliberate (`7f4ebc3`) | G9/R35 A02 → A.U0.30 (swap "(agent, 2026-07-23)", result owner-confirmed 2026-09-29) |
| HT.45 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:1915-1921` (:1915) | `9e418ed` | "A dedicated pass, prompted by owner request" | pruned as history | Pass header (H.17, B138) | none |
| HT.46 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:1963-1986` (:1963, :1967) | `500851c` | "Owner direction: apply the same schema … raising is allowed, but only in a controlled, documented manner, and only once it's proven every upstream caller actually handles it." | drifted | `src/crc_checks.py:4-6` states the raise without an actor. SPEC D.2:2624 calls bus calls "the one deliberate exception to "never raises"" | G3/R03 Rank (H2.20) |
| HT.47 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:1988-1998` (:1988) | `500851c` | "**Standing convention, confirmed by owner** … **keep the catch, skip the test, and document why inline**" | lost | "keep the catch" and "skip the test" have 0 hits at HEAD (docs and the two cited test files) | G5/R54 (RF016 placed there, `audit/refined/I7.md:7`; H2.21) → U35 Part E convention |
| HT.48 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:2039-2042` (:2040) | `3837a33` | "(owner request - "target production quality code")" | pruned as history | Pass header (H.17, B134) | none |
| HT.49 | 7a7f4b6 | `7a7f4b6^2:BACKLOG.md:2127-2128` (:2127) | `3ffc0c8` | "Owner asked for the same `src/README.md` pass again" | pruned as history | Pass header (H.17, B135) | none |

### Pre-filled outcomes (A.U0.15), checked at HEAD

| pre-filled | row | verified |
|---|---|---|
| Hostname ≤ 32 (`d725042`) → G6/R28 | HT.31 | Yes. The bound holds in code; only the owner words are gone. G6/R28's Rank does not yet cite `d725042` (`audit/refined/LEAD_APPLY.md:14`: the routing is recorded in G9/R33 only) |
| Captive DNS debug shape, "without adding too much complexity" (`639e992`) → G6/R24 | HT.01 | **Corrected.** G9/R33 calls it live, but HEAD reverses the shape (`DNSSRV` own logger, owner, 2026-08-07, `74cfa7f`), so it is pruned as history. G6/R24 keeps it only as the complexity principle for its U18 work |
| Captive DNS catch-all, "this input isn't usable, fall back" (`881c5f8`) → G6/R24 | HT.07 | Yes. Lost as text, the code holds; G5/R16 is the rule home (H.06) |
| `max_i2c_err` rename → resolved | HT.43 | Yes (`27ae6c6`) |
| `a6abe13` DNS-compression limitation | HT.36 | Drifted; home G6/R34 (RF013), not S01's "new req" |
| `5ddbcd3` per-service timeouts | HT.39-HT.41 | Lost; home G4/R54 (RF014) → U8 |
| `dd22d43` "adapt the test to the code" | HT.29 | Lost; home G2/R16 (RF015) |
| `645fe10` "keep the catch, skip the test" | HT.47 | Lost; home G5/R54 (RF016) |
| `cc911be` non-blocking goal (→ A.U0.22) | HT.12 | Lost; home G9/R36 C04 → A.U0.22 |
| `7f4ebc3`/`645fe10` CRC swap (→ A.U0.30) | HT.44 | Drifted; home G9/R35 A02 → A.U0.30 |
| C.11 `wrnno=17` rationale (`5860ad5`, dropped by `e5d2c43`) → pruned as history (RF023) | R19 | Yes. `wrnno=17` and `persist_window_ms` have 0 hits in SPECIFICATION.md; the principle is carried by G5/R54 (OR46.a (2), harmonization 30). It is an `e5d2c43` row, not one of the three merges |

## H1 outcomes (`audit/pass3/H1.md`, as G9/R33's State lists them), checked at HEAD

| H1 | outcome | evidence at HEAD (anchors re-taken at `46ba217`) | register home |
|---|---|---|---|
| H1.01 | drifted | BACKLOG.md:353: "the owner's standing answers (2026-09-22)" heads D1-D3 and the run order | G1/R02; G9/R35 A41 |
| H1.02 | drifted | SPEC:1894-1897 says "aggregation happens at the wiring level"; the actor and the networking-grouping reason are gone | G9/R27 |
| H1.03 | drifted | SPEC:1046 says "deliberately not a committed" with no "(owner, 2026-09-04)" | G9/R27 |
| H1.04 | drifted | CLAUDE.md:62-67 widens the precedent and drops "owner's explicit authorization each time" | G9/R28 |
| H1.05 | drifted | SPEC:2186-2187 has "if sharing a bus"; CLAUDE.md:237-240 keeps "never forget this" | G9/R37 (V22) |
| H1.06 | lost | CLAUDE.md:468 describes the layout only; the "all tooling config shall live in `pyproject.toml`" requirement is gone | G8/R47 |
| H1.07 | drifted | SPEC:6107 states the build-tooling contract without an actor | G9/R27 |
| H1.08 | lost | "imports happen once"/"never inside a function" has 0 hits in CLAUDE.md, SPECIFICATION.md and BACKLOG.md | G5/R48 |
| H1.09 | drifted | SPEC:4844-4846: the attribution is gone, and the false reason "a fork of vendored MicroPython, which CLAUDE.md forbids" is at :4845 | G9/R37 |
| H1.10 | drifted | `digital_twin/README.md` carries 2 "owner" mentions in total; the twin design decisions at :5 etc. are untagged | G9/R35 (+ G7/R05, R06, R08, R09, R26 Rank) |
| H1.11 | drifted | `tests_js/mock-server-put-matrix.test.js:2-4` has no owner tag (the only one is at :20) | G9/R27 |
| H1.12 | lost | `src/system_service.py:54-56` states no growth goal; "rsyslog" has 0 hits | G9/R24 |
| H1.13 | drifted (reason swapped) | `src/print_log.py:236, :247, :260` "broad on purpose: defense-in-depth against the Protocol in the abstract" | G5/R16 |
| H1.14 | drifted (reason swapped) | `src/api_response.py:91` "fires at most once per call", without the legacy-parity reason; SPEC:1794 | G9/R04 |
| H1.15 | drifted | `tests_hardware/bench/test_bus_concurrency_under_api_load.py:1-3` header has no owner attribution (owner mentions only at :223, :305) | G9/R27 |
| H1.16 | lost | BACKLOG.md:75-76 "(3) bus/sensor error-recovery robustness items above" points at nothing | LEAD/R29; G5/R16 Sources |
| H1.17 | lost | BACKLOG.md:75 "structural patterns above" points at nothing | G9/R19 (design-principles Part, U36b), the new conventions requirement beside G5/R48-R50 |
| H1.18 | drifted | The owner-confirmed design points (SGP40 VOC reset, FRAM pause gate, `get_chunk()` size 0, VOC restore, boot signature) carry no tag; for example, the only "owner" in `src/asy_fram_manager.py` is the logger owner at :89 | G9/R38 |

## Appendix: the other 29 of the 78 (reconciliation only, outside M.PROC.006)

`e5d2c43`'s first parent `47633ae` is the branch and its second parent `32e9a8e` is `main`. For these rows the merge
tree (`e5d2c43`) was checked for a reworded carry first, then HEAD. They are traced less deeply than the main table.

| id | site | trail | quote | outcome | evidence | register home |
|---|---|---|---|---|---|---|
| R01 | `f455d34^1:BACKLOG.md:473-481` | `75f2e11` | "`captive_dns.py` fixes (owner-authorized exception to the "don't edit `improved-quality/`" hard rule)" | pruned as history | One-time exception (H.17, B103); the fixes hold at `src/captive_dns.py:85-109, :187` | none |
| R02 | `e5d2c43^1:BACKLOG.md:697-716` | `b0f755c` | "What remains is purely mechanical, and is the owner's to schedule." | pruned as history | Executed by `e5d2c43` itself; its premise was false (S01 RP03.a) | G8/R63 |
| R03 | `e5d2c43^2:BACKLOG.md:57-94` | `41762dc`, `179a10c` | "Sort every class in `src/` to SPECIFICATION.md D.15's method ordering — HIGH PRIORITY (owner's ruling, 2026-09-13)" | lost | SPEC D.15:2730-2737 is the pre-ruling text; no sort item in BACKLOG at HEAD | G5/R50 (harmonization 27) → U10 |
| R04 | `e5d2c43^2:BACKLOG.md:323-327` | `e8d64f1` | "all five still need the owner's yes/no" | resolved | Carried as #37 (`e5d2c43:BACKLOG.md:581`); the owner's consistency decisions were applied and closed in `58abf8f`/`86fb067` (2026-09-24) | G9/R36 (A2-07) |
| R05 | `e5d2c43^2:BACKLOG.md:366-374` | `179a10c` | "Independent session - out of the ISL29125 branch's scope and not blocked on it (owner, 2026-09-14)" | pruned as history | Branch-scope tag, ended by the merge; the prefix question beside it is not an owner line | none |
| R06 | `e5d2c43^2:BACKLOG.md:403-405` | `b18618f` | "Left for the web lane's owner" | pruned (no decision) | "owner" means the lane owner | none |
| R07 | `e5d2c43^2:BACKLOG.md:408-436` (:434) | `179a10c` | "Independent session … (owner, 2026-09-14)" | pruned as history (tag) | The item itself was carried as #38 ("owner's standing direction (2026-09-11)", `e5d2c43:BACKLOG.md:609`); HEAD has it at BACKLOG.md:22-26 | none |
| R08 | `e5d2c43^2:BACKLOG.md:438-453` (:451) | `179a10c` | "Independent session … (owner, 2026-09-14)" | pruned as history (tag) | The item was resolved (`e5d2c43:BACKLOG.md:327` #23, "fixed (owner decision, 2026-09-18)"); SPEC:1949 | none |
| R09 | `e5d2c43^2:BACKLOG.md:455-476` | `05f4746` | "Out of scope for the ISL29125 promotion (owner, 2026-09-13)" | resolved | Frozen-asyncio probe added in `12640c2`: `scripts/test.sh:97` | none |
| R10 | `e5d2c43^2:BACKLOG.md:478-481` | `706f9e0` | "the owner's ruling is to leave the specification exactly as it stands … and tidy this up in a session of its own" | resolved | Part M (SPEC:6592); H2.82 | none |
| R11 | `e5d2c43^2:BACKLOG.md:496-505` | `2ad5d9e` | "C.11.5 (the project owner's twenty settled requirements …)" | stands | SPEC M.1.1:6606 "Settled requirements — the project owner's list" | none |
| R12 | `e5d2c43^2:BACKLOG.md:530-531` | `179a10c` | "Independent session … (owner, 2026-09-14)" | pruned as history (tag) | Branch-scope tag | none |
| R13 | `e5d2c43^2:BACKLOG.md:533-543` | `3a94eb2` | "tightened from "no hard numeric cap" to 3 lines per block on 2026-09-14 (owner; CLAUDE.md records it)" | resolved | Carried as #42 and closed on 2026-09-19; CLAUDE.md:412-420 | none |
| R14 | `e5d2c43^2:CLAUDE.md:297-315` (:302, :313) | `3a94eb2` | "tightened from "no hard numeric cap" by the project owner, 2026-09-14" | stands | CLAUDE.md:416-417 "tightened from "no hard numeric cap" by the project owner on 2026-09-14" | none |
| R15 | `e5d2c43^2:SPECIFICATION.md:441-445` | `f05f82d` | "dev-only, by the project owner's own scoping decision" | stands | SPEC:6601 "Scope is the `dev` variant only (M.1.1, requirement 18)", under the owner's list; SPEC:2190, :5900 | none |
| R16 | `e5d2c43^2:SPECIFICATION.md:452` | `715cd73` | "\| Chunk \| Owner \| Same as wozi? \|" | pruned (no decision) | Column header ("chunk owner") | none |
| R17 | `e5d2c43^2:SPECIFICATION.md:1261` | `90e5ebb` | "old bench logs from development have no reuse value (owner, 2026-09-14)" | pruned as history | The rationale justified `main`'s renumbering, which did not merge; HEAD SPEC:1938 carries the branch's numbering ("12 is retired, not reused") | none |
| R18 | `e5d2c43^2:SPECIFICATION.md:1272` | `a195c4c` | "disjoint from any owner's own range where the logger is reached through" | stands (no decision) | Verbatim at SPEC:1949; "owner" means the logger owner | none |
| R19 | `e5d2c43^2:SPECIFICATION.md:1517-1522` | `5860ad5` | "keeping it as an invariant check was considered and rejected (owner, 2026-09-13)" | pruned as history (RF023) | `wrnno=17` and `persist_window_ms` have 0 hits | G9/R33 (RF023); principle in G5/R54 |
| R20 | `e5d2c43^2:SPECIFICATION.md:1719-1722` | `179a10c` | "Migrated out of BACKLOG.md on 2026-09-14 (owner's direction)" | stands (migrated) | SPEC:6792 "A measured property of the part … not an open" | none |
| R21 | `e5d2c43^2:SPECIFICATION.md:1772-1775` | `2ad5d9e` | "The twenty decisions the promotion was designed against, as the project owner settled them." | stands | SPEC M.1.1:6606-6608 | none |
| R22 | `e5d2c43^2:SPECIFICATION.md:2007-2024` | `080cde3` | "**"Starter" is a role, not a name** (owner, 2026-09-14)" | lost | SPEC D.15:2732-2734 still classifies starters by prefix | G5/R50 → U10 (restored verbatim, `audit/actions/U10.md:903`) |
| R23 | `e5d2c43^2:dev_legacy/README.md:49` | `7be762f` | "**pulled up** — confirmed by the project owner directly on the board" | stands | `dev_legacy/README.md:49` keeps the owner confirmation | none |
| R24 | `e5d2c43^2:dev_legacy/README.md:98-104` | `715cd73` | "running its scripts needs the project owner's go-ahead in the session that runs them" | resolved | The ISL29125 has since run on silicon (`tests_hardware/README.md:177-188`); the go-ahead rule is in CLAUDE.md | none |
| R25 | `e5d2c43^2:src/sensortask_dev.py:315-346` | `3a94eb2` | "the same 20-owner enumeration" | pruned (no decision) | "owner" means owning objects; the file is generated now | none |
| R26 | `e5d2c43^2:tests/test_sensortask_dev.py:991-1011` | `3a94eb2` | "the same 20-owner enumeration" | pruned (no decision) | As R25 | none |
| R27 | `e5d2c43^2:tests_hardware/README.md:142-143` | `1ea08ad` | "Three properties of this specific rig, all confirmed by the project owner or measured directly." | stands (facts; actor clause gone) | `tests_hardware/README.md:177-188` (latched WS2812, coverable sensor, breakout red LEDs) | none |
| R28 | `e5d2c43^2:tests_hardware/README.md:309-315` | `699836e` | "Settled as acceptable degradation rather than a robustness gap (owner, 2026-09-13)" | lost | No E31/W71/W72 expectation in `tests_hardware/README.md` | G5/R25 → U35 (S01 RP03.b) |
| R29 | `e5d2c43^2:tests_hardware/bench/test_end_to_end_timing.py:171-176` | `3a94eb2` | "FRAM is NOT held to an empty log, and that is the point (owner's ruling)" | lost | `tests_hardware/bench/test_end_to_end_timing.py:169` `assert_module_error_log_empty(dut_ip, "FRAM")` | G5/R25 → U35 |

## Lost rows with no register home (deltas to A-C)

**None.** Every lost row has a register home:
- in the main table: HT.07/HT.09 → G5/R16; HT.12 → G9/R36 C04; HT.29 → G2/R16; HT.39-HT.41 → G4/R54; HT.47 → G5/R54;
- among the H1 outcomes: G8/R47, G5/R48, G9/R24, LEAD/R29, G9/R19;
- in the appendix: G5/R50, G5/R25.

So no OR106.a delta is raised.

Two register-text notes for the owning units. Neither is a lost row:
- **G6/R28 (U6/U18)**: the Rank does not cite HT.31's owner quote, "adapt the schema to fit the actual value"
  (owner, 2026-07-27, `d725042`). G9/R33 holds that routing only.
- **G6/R24 (U18)**: the "live" label G9/R33 gives HT.01 overstates it. The debug shape was reversed by the owner on
  2026-08-07 (`74cfa7f`), and only the complexity principle remains.

## Notes for G9/R33

- The 78 aggregate covers four merges, not three: `e5d2c43` contributes 28 paragraphs and `f455d34`'s first parent
  contributes 1. For the three 2026-07-30 merges, the second-parent count is 49 paragraphs (60 lines).
- HT.23's closure rests on an agent claim from `8784c66` ("no such config param exists on the CYW43/rp2 port"). It
  was not re-verified here: no MicroPython source was read in this step.
