# R5 unit weblog: the web server and logging side of the owner's five, the /status walk, the lock sites (lead, 2026-11-09)

## Read first
`S/u35r/r1/common_r1.md` (binding, its "Every level", "The platform first", the goal line and "Ask before removing a
feature" above all; labels `weblog_`). S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
Then `S/u35r/findings/FINDINGS.md` 12.104 (LEVELS_1 items 1 and 2), 12.107, 12.108, 12.111 (4), 12.117, 12.119-12.120;
`S/u35r/r5/LEVELS_1.md` items 1-2, `S/u35r/r5/STRETCH.md` section 1, `S/u35r/r5/COMPLETE_1.md` item 4,
`S/u35r/r5/DESIGN_FU.md` row on `_config_lock`, `S/u35r/r5/LEVELS_3.md` item 2 (`wifi_mode_lock`),
`S/u35r/r5/HANDBACK_BFIX.md` (the `err_q()`/`wrn_q()` form and its write-behind). Code: int `S/wt-u35int` at f1a734f5.

## Owner (verbatim)
- 2026-11-07 17:57:27: "Go to all, be sure you really found all such occurrences, and it won't happen again." - the go
  for (1) the error-log reset sequential and (2) a refused or dropped connection closing before its FRAM entry.
- 2026-11-09 19:11:51: "This way of thinking and finding solutions which are minimal and optimal at the same time
  through smart design was one of my primary goals of the audit."
- 2026-11-09 18:30:08: "Before removing any function which could be a feature which is just unused, ask me"

## Your work (worktree `S/wt-weblog`, branch `audit/weblog` from int `f1a734f5`; create it; commit locally, never push)
1. ResetErrors runs its sources one after another, no task per source (LEVELS_1 item 1). Whatever existed only to
   serve concurrent resets (the in-flight reset mask, `tests/test_asy_print_log.py:1125-1181`'s reason) is internal
   mechanism the change replaces: it goes if nothing else needs it; say what and why. The answer ("Failed" per source)
   stays as specified.
2. A refused or dropped connection releases its count and closes before it awaits its FRAM entry, exactly as approved
   (LEVELS_1 item 2: the entry is in RAM before the first await). Keep the awaited entry after the close.
3. STRETCH section 1's fix: the errcount part of `/status` writes each entry as one formatted fragment, the bytes
   identical; `_shape_errcount_entry` is internal and goes with its test calls adapted
   (`tests/test_asy_webserver_service.py:3719`, `:3738-3745`).
4. No lock held across a FRAM wait (12.111 (4)): `_status_lock` (`asy_webserver_service.py`), `_set_lock`/`owner_lock`
   (`asy_base_classes.py` config GET/PUT and the BMP3XX/SCD30 rungs), `_config_lock` (`asy_config_manager.py`
   `write_config()`), `wifi_mode_lock` (NTP and Wi-Fi entries), `_threshold_lock` (`asy_isl29125_driver.py`). Smallest
   form per site: the entry logged with the `_q` form (recorded and printed at once, written behind), or after the
   release where the order of events needs the await. List every other `err_s`/`wrn_s` call made under any lock you
   find; change those of the same kind the same way.
5. Tests first (seen red on f1a734f5 where they pin a change): reset sources in sequence (the gather pin at
   `tests/test_asy_webserver_service.py:1294-1301` changes); a refused connection's slot and close come before its
   entry completes, while the store's chunk write is held; errcount bytes identical to today's for every logger shape;
   per lock site, a holder that logs never makes another waiter wait on FRAM (rounds, never wall clock).
6. Docs, current state, fewest lines: the parts that state these behaviours (grep for the reset, the refusal trace,
   `_status_lock`, `owner_lock`, `_config_lock`, `wifi_mode_lock`), and the F.3 and C.8 rows they name. No history.

## Never
Never remove a feature (common_r1); never change a wire byte, a `/status` byte or a stored format. Never edit `ext/`;
never read `arduino/`; never open `/root/.claude/`; no hardware. No `gc.collect()`, no new delay, no per-request
allocation added. `src/asy_wifi_service.py`, SPECIFICATION.md, CLAUDE.md, `devices/` and generated modules only through
common_r1's credential filter; never print, copy or write any Wi-Fi credential or the hotspot password. Scratch copies
of source only under your own `S/u35r/r5/ftmp_weblog/`.

## Checks
Each touched test file at both GC stages while fixing; `lint_direct.sh`; the three mypy passes; then the gate as
common_r1 says under `S/u35/lead/heavy.lock` holding the line `weblog` (unit crceng may hold it: wait while it exists;
`rm` it, literal path, its own command, after). Sizes and `imageFreeBytes` against f1a734f5.

## Limits and hand-back
Write only the files these items need and their tests. One commit. Budget about 2 % of the week. Hand back by 03:00
UTC: `S/u35r/r5/HANDBACK_WEBLOG.md` (at most 30 lines, as common_r1 says, with need against cost per changed
operation), your commit, one line per headline result, and last "nothing of mine is running".
