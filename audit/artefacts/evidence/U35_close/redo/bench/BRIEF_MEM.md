# Root cause, then fix: the /status MemoryError under concurrent readers (lead, 2026-11-05)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `mem_`); `S/u35r/bench/ROOT_CAUSES_20261105.md` item 8 (the bench session's
measurements and its inferred lead) and `S/u35r/bench/repro_status_load.py` (its load, for reference: it targets a
board, never run it); SPECIFICATION.md Part I (I.3 the piece writer, I.4 the memory scheme, and the heap-measurement
rules near "A contiguity figure needs its sample point"); CLAUDE.md's memory-safety bullet. S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## The failure (silicon, control image at gc.threshold -1, dev)
Three clients reading `GET /status` every 50 ms get `500` on 8-14 of 46 reads; the console shows `WEBSERVER Microdot
caught: memory allocation failed, allocating 242 bytes` (failed sizes 242-257 B), logged as `WEBSERVER E23`. One reader
never fails, two rarely. `/measurements` under the same load never fails. One `/status` answer is 7,369 B and takes
1.4 s. The threshold image was not tried.

## Your work, in order (worktree `S/wt-mem`, branch `audit/mem`, at `5f763f25`; commit locally, never push)
1. **Root cause.** Find what holds the heap when the allocation fails, and why the design lets concurrent `/status`
   requests reach it: what one request holds and for how long (its pieces, the config reads it makes), how many can
   overlap under the connection ceiling, against the board's free heap after boot. Reproduce on the twin at the
   board's heap scale, as Part I's measurement rules describe; a measured mechanism, not the bench's inference.
2. **The fix, at the source, in its smallest form,** if step 1 finds the mechanism by 15:15 UTC. CLAUDE.md's ladder
   binds: no threshold, no `gc.collect()`, no catch, no lower connection ceiling as the fix, no larger heap. The
   response's bytes, its routes and the error numbers stay as they are (the website reads them). Its test comes
   first: it pins the property that failed (for example the bytes concurrent `/status` builds hold at once), seen red
   on `5f763f25`, then green.
3. If step 1 is not done by 15:15 UTC, stop and hand back the diagnosis as far as it goes. The image then ships
   without a fix, and the bench measures it as a known open defect.

## Checks (light runs only, at most twelve; single test files and single twin processes)
After `S/u23/rebuild.sh S/wt-mem`: `tests/test_asy_webserver_service.py`, `tests/test_asy_webserver_connections.py`,
your new test, and the twin webserver files (`tests/test_digital_twin_webserver*.py`), each at both GC stages, `TEST_DEVICE=dev`
and `wozi` where per-device; no `MemoryError` or "memory allocation failed" in any log. Lint, the three mypy passes,
`tests_scripts/test_comment_block_cap.py`. A firmware build (`scripts/build_firmware.py dev`, its `imageFreeBytes`)
only under the heavy-slot rule: check `S/u35/lead/heavy.lock` is absent, touch it, run, `rm` it as its own command.

## Limits
- Write only `src/asy_webserver_service.py`, the webserver tests, and the SPECIFICATION.md Part I or H sentence your
  fix makes wrong. Bytecode grows only by the admitted fix: state by how much.
- Hand back by 15:45 UTC whatever the state. Budget about 1.5 % of the week.

## Hand-back
`S/u35r/bench/HANDBACK_MEM.md`, at most 30 lines, and return its path: the mechanism with its evidence (figures, the
run labels), the fix's commit and lines per file, the test (red, then green), the checks, `imageFreeBytes` if built, and
what stays open. Last line: "nothing of mine is running".
