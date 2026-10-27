# HP1: the per-boot heap holder and the restart question (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then item 2 of `S/u35r/handbacks_redo/CMr1h.md` and the heap part of `S/u35r/handbacks_redo/CMr1g.md` (their probes
and logs). Worktree and branch: in your launch message (the integration head). Logs in `S/u35/laneB/hp1/`.

## The facts so far
In tests/test_digital_twin_ntp.py, every arzi re-boot in the same test process keeps exactly 147,488 bytes after a
collect, at each of 7 re-boots: 1194 objects of other types, 267 tuples, 86 strings, 73 lists, 61 byte arrays, 52 dicts,
13 functions, 4 floats. The qstr pool is flat. No container reachable from the loaded modules grows, so the holder is
reached through an instance, a closure or a native object. Silicon boots once, so the per-boot step cannot build up
there; a leak on the supervisor's task restart could, and that is not yet shown either way.

## Items, in order
1. The silicon question first. In one booted twin (at least dev and arzi), make the supervisor restart each kind
   of supervised task many times (20 or more each: a reader, the webserver, wifi, ntp, the status loop, every kind
   the generated main() starts), and measure mem_alloc after a collect at each restart. It is flat after the
   first few, or name what grows, per restart, with numbers. Both GC stages. This settles whether a task restart
   leaks on silicon.
2. The per-boot holder. Name it, with numbers. Candidates to rule in or out, cheapest first: the twin's registries
   (machine.Timer, Pin, I2C/SPI bus singletons, the WDT, network.WLAN, the FRAM chip model), the asyncio IO queue
   (a ThreadSafeFlag or socket still registered in the poller), `micropython.schedule`'s queue, and a module- or
   class-level reference in src/ or the generated modules. A bisection (tear a registry down between boots, and the
   step goes away) is a proof; a reading alone is not.
3. Decide, with the evidence: a holder in digital_twin/ or the test harness is a test-process artefact (say so; fix
   it only if it is a twin defect, with its test); a holder in src/ or a restart that grows is a firmware defect,
   under redo_common's defect rules (red-first test, both stages).
4. Seams: at about 80 tool calls, commit what is green and hand back with what is left.

## Hand-back (the file, per redo_common)
Commits; the restart measurements per task kind; the holder with its proof; the verdict; any question for the owner
in prose with a recommendation; last line "nothing of mine is running".
