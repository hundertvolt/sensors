# R5 unit G: the firmware's bounds to their sources, and its simplifications that drop nothing (lead, 2026-11-10)

## Read first
`S/u35r/r1/common_r1.md` (binding, all of it - the two source rules, the retired-code rule; label `g_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. FINDINGS 12.137, 12.141, 12.143,
12.144, 12.148; `S/u35r/r5/GIVEUP_1.md`, `GIVEUP_2.md`, `CONSENT_1.md` and their ledgers (the sites and evidence);
`CREDIT.md` and `CREDIT_ledger.tsv` (the credits). Code: int `S/wt-u35int` at a293d6f9. Unit C writes at the same time
(build chain and website: `scripts/`, `toolchain/`, `buildgen/` host code, `js/`, `tests_js/`); you own `src/`, the
device TOMLs and their tests. The JS mirror rule (Part G) holds: a firmware constant the website mirrors changes in
both, in your commit.

## Owner (verbatim)
- 2026-11-09 22:27:31: "... don't drop real features and don't introduce or reintroduce gaps. Lean, functional, no
  losses, no gaps, efficient by smart design appropriate for limited devices like the rp2"
- 2026-11-09 21:57:36 / 21:36:14: the give-ups the audit added are overkill; "find a solution without that many magic
  numbers and which generalizes cleanly."
- 2026-10-27 (typing-only checks): "if the check you remove really solely covers typing breakages and nothing else it
  can go (option b)"

## Your work (worktree `S/wt-g`, branch `audit/g` from a293d6f9; create it; commit locally, never push)
Bounds (each keeps its source in one comment line, or goes):
1. Webserver close path: no `wait_for_ms` around `writer.wait_closed()` (:704-ish) and no bound on the proxy's
   `aclose()`/`wait_closed()` - at v1.29.0 `Stream.wait_closed()` is `self.s.close()` with no yield
   (`extmod/asyncio/stream.py:19-21`, `aclose` the same, :220); the try/except and its warning stay.
2. UART: `cancel_read_timeout()` waits for the holder's acknowledgement with no deadline (the holder acknowledges in
   every `ready()` round and on exit; the write gate's hold-off sleep under the bus lock is up to 1,500 ms, so today's
   1,000 ms gives up on a healthy holder and persists W55). `_CANCEL_ACK_TIMEOUT_MS`, `cancel_unacknowledged` and W55
   (its catalog row deleted, none reserved) go; `clear()` stays (OR36.a (3)). One Class B changelog entry.
3. Captive DNS: the receive-failure backoff (0.5 s doubling to 5 s) becomes the legacy fixed 3 s pause
   (`_ERROR_RETRY_WAIT_S`); its three constants and rows go; C.9's backoff convention states the current form.
4. Config store: `delete_file()` removes once (no retry); the console line and the "command incomplete" record stay.
5. ISL29125: the calibration candidate stays readable until the next run starts or a reboot (`_CAL_HOLD_MS` and its
   row go); `_CAL_WINDOW_MS` keeps the owner's bounded run (2026-09-13) with its count's reason named or derived.
6. DNS: derive per-server timeout and tries from the platform's own resolver that legacy's `getaddrinfo()` used (lwIP
   at the pinned MicroPython: its retry interval and count, from `lib/lwip` and rp2's lwipopts, cited by line),
   weighing C.8's NTP hold under the Wi-Fi mode lock; `dns.tries` and its loop stay only if that gives more than one
   try. The HTTP per-call 5 s and outer 15 s: derive from silicon's longest legitimate request (/status, 2,591 ms
   max, its record) if a derivation holds, else name the source as it is; `js/poll-manager.js`'s 15 s follows the cap.
7. UART `_POLL_JITTER_MS`: if driver-internal, derive from one frame's wire time; if a protocol recovery timing
   (Class A), name its source and leave the value (owner 2026-11-03: "Keep the UART as is"). The link's
   `_HAZARD_RECOVERY_ATTEMPTS` (dev only) by construction, with the bench script's mirror; `_BACKOFF_MAX_MULT`'s
   comment names changelog A15.
Simplifications (same behaviour, leaner form; tests rewritten first):
8. UART's typing-only guards: the five "kept to narrow the Optional" branches take the module's local-annotation form
   (:577), the isinstance halves on typed arguments and same-image callback returns go; range checks and codes stay.
9. Deferred flash write: validate and stage, push, then one write - no per-store Event, `defer=`, `commit()` or hooks;
   "a refused setting costs no flash write" stays pinned by its tests. Medium risk: the flash write path.
10. Reset-in-progress flags (`_closed`, `writes_closed`/`_closed_for_reset`, `_writes_closed`, `_reset_armed`,
   `_reset_decided`, `_feed_owned`, `_force_watchdog_starve`): one phase value; the same refusals, closed writes and
   stopped feeds, pinned by today's tests.
11. UART discarded-byte accounting: verify first that the DMA ring's received total gives E89 the same condition; only
   then replace the 19 counts and the wrapper. If not equivalent, leave it and say why.
12. Credits in `src/`, `buildgen/` product rules and device TOMLs: the "owner-reviewed, 2026-11-06" suffix goes ("(agent,
   date)" stays); every audit-era STRETCHED/UNBACKED credit in your files takes its ledger's plain form. Credits dated
   before 2026-09-25 wait for the owner's answer - leave them.

## Never
Never remove a feature beyond the items above; never change a stored FRAM byte, a CRC value, a wire byte or a /status
byte except W55's removal from the catalog; never touch C's files beyond item 6's JS mirror line. Never edit `ext/`;
never read `arduino/`; never open `/root/.claude/`; no hardware. No `gc.collect()`, no new delay, no new bound or
mechanism without a source. Credential filter as common_r1 says. Scratch only under `S/u35r/r5/ftmp_g/`.

## Checks and hand-back
Touched test files at both GC stages while fixing; `lint_direct.sh`; three mypy passes; the gate as common_r1 says,
under `S/u35/lead/heavy.lock` holding `g` (unit C may hold it: wait while it exists; `rm` it, literal path, its own
command). Sizes (armv6m) and dev `imageFreeBytes` against a293d6f9. One commit; budget about 3 % of the week. Hand
back by 13:00 UTC: `S/u35r/r5/HANDBACK_G.md` (at most 40 lines: per item what went, its source, the figure), your
commit, one line per headline result, and last "nothing of mine is running".
