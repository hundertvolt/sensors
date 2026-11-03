# B1 falsification: the lead's check of each refutation at the source (lead, 2026-11-03 00:04 UTC)

The falsifier (`FALSIFY.md`) refuted claims 1, 2 and 11 of `FALSIFY_BRIEF.md`; claims 3-10 and 12 stand. Each refutation
was read at the source before anything was changed. Fixes on `audit/r1-b1`: `160bd939` (review), `846b2a1e` (these).

| claim | refutation | verified | outcome |
|---|---|---|---|
| 1 | on a full heap a logger call allocates before its entry records the overflow | yes: a star-call builds its argument tuple, `err_s()` its coroutine; the probe measured 32 B (`wrn`) and 152 B (`err_s`) | accepted as a stated limit (agent, 2026-11-02): a C-stack overflow and a heap without room for one log call at once; the `MemoryError` takes its own path outward, the watchdog stays the backstop; SPECIFICATION.md F.1 says so. Restoring 118 explicit calls is item 1 undone |
| 1, 11 | the guard test misses a dropped `e` in `_shutdown_sequence`'s outer handler and a log after an early `return` | yes: the exemption keyed on the whole function; `_logs` read every statement | fixed: only the unbound `pass` handler is exempt; a log counts only before any statement that can leave the handler; both planted breaks now fail the test (`b1L_plantA`, `b1L_plantB`), new cases for both |
| 2 | at level 1 a `MemoryError` logged as a warning prints nothing | yes: six sites (`asy_config_manager.py:546`, `asy_webserver_service.py:736`, `:740`, `:970`, `:973`, `:975`; `tools/memlevel_scan.py`); none above WARN | fixed test-side: the memory gate's unit tests and twin scenarios boot at WARN (2), so both levels print (owner's option 1, "error level or above") |
| 2 | on the board nothing logged during construction prints at any level | yes: the boot entry builds at level 0; the stored DebugLevel applies in `SystemService.setup()`; ordinary construction lines were always silent there, a caught `MemoryError` printed through `console()` until (d) | put to the owner (clarification (d2)); about seven construction-time catches |

Outside the claims: the no-autostart boot entry's start line prints at import at every level (B8's file, listed for B8);
a reset during a logger's setup read is overwritten by the restore (unreachable on the device; the unit's hand-back
says so).

The gate on `846b2a1e` (`b1L_gate`): lint clean; the unit tier at 32768 and the dev twin suite at both stages and its
harness at -1 passed; the unit tier at -1 had one red, `test_every_python_and_shell_file_opens_with_a_header`, on
`tests/_tmp/rgi/sensortask_fixture.py`, a scratch module `tests/test_digital_twin_run_generic_integration.py` writes
while the backgrounded tests_scripts tier scans. Root cause: the check's glob entered the concurrent scratch the other
scans skip; reproduced with a planted header-less file there, fixed in `93224dab`. A container restart killed the
harness at 32768; it and the -1 unit tier rerun on `93224dab` (`b1L_gate2`).
