# Read-only diagnosis: where dev's heap went (lead, 2026-11-05; for the last round's /status fix)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `memdx_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then
`S/u35r/bench/ROOT_CAUSES_20261105.md` items 8, 12 and 13 (the bench's silicon measurements), and FINDINGS 12.13,
12.15 and 12.17 in `S/u35r/findings/FINDINGS.md`. Your worktree: `S/wt-memdx` (detached at `767f0d79`, a throwaway;
run `S/u23/rebuild.sh S/wt-memdx` before any run). The bench's evidence is readable as
`git show origin/claude/u35-bench-campaign:audit/artefacts/evidence/U35_close/redo/hw_round1/<file>` (its
`heap_probe/heap_maps_20261105.txt` holds the maps); history through `git log`/`git show` with `':!arduino'`.

## The facts
- `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` on silicon, final image: 69,312 B allocated
  before the build, 128,384-128,576 B after it, against the owner's 100,000 B bound. The bound's own comment cites
  "every reading of a fully built dev graph is 87,760-87,968 B"; an earlier record closed on 84,112 B.
- The bench's heap probe, also under `mpremote run`: 57,632-58,224 B free after `gc.collect()` at idle, four boots.
  SPECIFICATION.md Part I.6 and Part N assume about 105,000 B free after boot.
- `/status` under 3 readers on the final image (lock plus drain): 3 of 156 answered 500 at a 250 B allocation, lowest
  sampled `MemFree` 4,544-9,296 B. The twin gave 0 at 3 readers (12.13), and still fails some at 6, with a finished
  response that stays live (holder unknown).

## What to answer
1. **The 69,312 B before the build:** what it is (the script's own compile under `mpremote run`, its rendered
   includes, module objects of the imports it does before the baseline, anything else), estimated per source.
2. **The 84-88 KB readings:** which image, commit and script version they came from, and whether that script read
   its baseline at the same point. Then the difference to today, split into measurement (the script) and product
   (the built graph), with the commits responsible. Name the largest single contributors.
3. **Production's own idle free heap** under `main.py` (no `mpremote run`): any record that gives it, or the best
   estimate from 1 and 2. Say whether it, rather than the probe's figure, is below Part N's 68,790 B demand.
4. **The live finished response** (12.13): from the code (`src/asy_webserver_service.py`, `ext/microdot.py` read
   only), what can still reference a `/status` response's pieces or body after its last byte is written, for how
   long. Confirm in the twin if one light run can show it.
5. **What the last round's fix should start from:** one paragraph, the smallest design that keeps `/status` within
   the heap 3 tells you dev really has, under `max_connections` readers. No code.
Mark each statement measured, read in the source, or inferred.

## Limits
Read-only: write only your hand-back and scratch files under `S/wt-memdx/ftmp/` (deleted before you hand back). Light
runs only, at most ten, each single-file or one twin script; the heavy slot is the lead's until about 18:30 UTC, then
take it as common_r1 says for anything multi-process. No real hardware. Budget about 1 % of the week; hand back by
21:30 UTC.

## Hand-back
`S/u35r/bench/HANDBACK_MEMDX.md`, at most 40 lines, and return its path. Last line: "nothing of mine is running".
