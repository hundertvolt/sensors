B1 falsification, written by the agent (Mon Nov  2 23:50:32 UTC 2026)

Target `39f1615b` (base `4516e60e`), worktree `S/wt-b1f`, left clean (`git status` empty; only the rebuild's ignored
`build/` output added). Eight runs through `S/u35/lead/run.sh`, logs in `S/u35/lead/b1f_*.log`: `b1f_rebuild`, `b1f_ast`
(AST listing of every broad and every MemoryError handler in `src/` and `build/generated_src/`), `b1f_sizes`, `b1f_probe`
(failed: no `.frozen` on the path, rerun as `b1f_probe2`), `b1f_probe2`, `b1f_plant`, `b1f_full` (failed: a module-level
global grew on the full heap, rerun inside a function as `b1f_full2`), `b1f_full2`. Probe scripts:
`S/u35r/r1/B1/b1f_tools/{handlers,probe,probe_full}.py`; the base copy of `asy_print_log.py` the probes ran against is
`S/u35r/r1/B1/b1f_base/`. I read the claims, the diff, the code and the tests, and did not open this unit's hand-back,
action list or review notes.

Result: claims 1, 2 and 11 are REFUTED. The other nine stand.

## Per claim

### 1. Every broad handler still records a C-stack overflow; the checker catches any break: REFUTED (two ways)
- **The record is lost on an exhausted heap, where it used to be made.** The static part is right. `b1f_ast` lists 132 broad
  handlers. Each one either hands its own name to one of the listed entries in a top-level statement, starts with
  `report_if_fatal(e)`, ends in a bare `raise` or is one of the two exempt sites. Also, each entry's own first step does
  record (`src/asy_print_log.py:89-95`, `:111-115`, `:244-248`, `:258-262`). The problem is that the **call** into
  `err/wrn/one/evt/all` (gathering `*args` into a tuple) and into `err_s/wrn_s/_err` (building the coroutine object)
  allocates before that first step runs. At `4516e60e` the record was the handler's first statement, an allocation-free
  `report_if_fatal(e)`.
  - `b1f_probe2`, P1, heap locked, a real overflow (`args ('maximum recursion depth exceeded',)`): `err`, `wrn`, `one`,
    `evt`, `all`, `err_s` and `wrn_s` each "raised MemoryError NOT recorded". `report_if_fatal` and `err_nomem` each
    recorded.
  - `b1f_full2`, a really full heap (not locked): `wrn` "raised: memory allocation failed, allocating 32 bytes | NOT
    recorded". `err_s` "allocating 152 bytes | NOT recorded". `report_if_fatal` and `err_nomem` recorded. `err` happened
    to find one free block in that fill.
  - So a handler like `except Exception as e: await self.pr.err_s("...", e, ...)` on a full heap raises MemoryError instead
    of recording, and the overflow is gone. A supervised task's end is then logged as a MemoryError. An unsupervised one
    reaches `report_unretrieved`, which prints but records nothing. Either way `fatal_reported()`
    (`src/asy_system_service.py:551`) stays False and the reboot does not happen.
- **The checker does not catch every break (planted, `b1f_plant`).**
  - Plant 1: drop `e` from `_shutdown_sequence`'s outer handler, `src/asy_system_service.py:494`
    (`err_s("Shutdown sequence failed", errno=...)`).
  - Plant 2: insert `if self._force_watchdog_starve: return` before the log in `_reset_when_due`, `:426`.
  - Result: `tests_scripts/test_fatal_report_sites.py` "27 passed" with both plants in place. Restored with
    `git checkout -- src/asy_system_service.py`.
  - Causes: `_EXEMPT` (`tests_scripts/test_fatal_report_sites.py:21`) exempts the whole function `SystemService._shutdown_sequence`,
    which holds two broad handlers (`:467` the await, `:492` the outer one). The claim names only the await as exempt.
  - `_logs` (`:52-57`, used at `:133`) accepts a qualifying call in any top-level statement, after an early exit, and with
    any receiver whose method has a logger entry's name.
- The two exempt sites themselves stand.
  - The await at `:467` runs after the supervisor task is proven done (`:451-452`). The supervisor reads the record only at
    a pass start, after its `_feed_owned` park check (`:546-551`), and `src/asy_system_service.py:797-804` never restarts it.
  - `report_unretrieved`'s `except Exception: pass` (`src/asy_print_log.py:135`) runs at the loop's top, where the C stack
    is shallow.

### 2. Level 0 prints nothing; from level 1 on every former `console()` MemoryError still prints; no site silent at every level: REFUTED
- **The first sentence stands.**
  - Every `print`/`print_exception` in `src/` is level-gated: `src/asy_print_log.py:95,115,130-131,180`.
  - Microdot's `print_exception` is rebound to the gated `_print_exception` (`src/asy_webserver_service.py:564`,
    `:799-809`). It is looked up at call time at `ext/microdot.py:1426,1536,1561`, and Microdot's `debug` prints stay off.
  - In the generated modules, besides the admitted `sys.print_exception(ended)` (`sensortask_<d>_main.py:44`), each
    `sensortask_<d>_main_noautostart.py:23` prints its manual start line at import, whatever the level (see "Outside the claims").
- **Not silent at every level? False: construction-time sites are silent at every stored DebugLevel.**
  - The product boot entry calls `asyncio.run(main(watchdog=watchdog))` (`build/generated_src/sensortask_wozi_main.py:32`),
    so `build_system(debug=None)` builds every logger at level 0.
  - The stored DebugLevel is applied only inside `sysfunct.setup()` (`src/asy_system_service.py:752-755`), which is second
    in `_collect_setups()` (`sensortask_wozi.py:188`).
  - So any caught MemoryError at construction, or in `fram.setup()`/early `sysfunct.setup()`, now prints nothing, whatever
    level the device is set to. At `4516e60e` `console()` printed it at every level. Sites:
    - `src/asy_print_log.py:149-154` (history ring)
    - `:276-281` (`get_chunk` MemoryError)
    - `src/asy_fram_manager.py:106-112` (chunk check buffer, built inside `get_chunk()` at `:705`, called from those
      constructors)
    - `src/asy_sgp40_driver.py:242-248` (backup chunk; at the base its below-level line printed through `console()`)
    - `src/asy_uart_comm.py:247` → `:343-344` (the frame `RegionBuffer`s, dev)
  - `b1f_probe2` P3: product construction (`make_logger(LogConfig(None, 10, None), ...)`) with a refused ring, then
    `set_level(5)`. The base printed "C PrintLog: history allocation failed: probe text C". The head printed nothing, at
    level 5 too.
  - `tests/test_asy_print_log.py:480-489` pins this silence for the product's own default (level None).
- **"From level 1 on every one still prints"? False at level 1 for the ones logged through `wrn`/`wrn_s`.**
  - At the base, `_line`'s below-level branch printed a caught MemoryError among any entry's arguments.
  - `b1f_probe2` P2 at DebugLevel 1: the base printed "H probe text W" and "H probe text WS". The head printed nothing.
  - Product sites: `src/asy_config_manager.py:537-546` (json.load exhausting the heap, `wrn_s`),
    `src/asy_webserver_service.py:970-977` (server start, `wrn_s`/`wrn`) and `:733-740` (broad handlers, `wrn_s`).
  - The commit's own `tests/test_asy_print_log.py:1622-1631` asserts `pr.wrn("below its level:", err)` prints nothing at
    level 1.

### 3. Every product builder/user hands its logger: STANDS
- `UDPSocket`: `src/asy_captive_dns.py:59`, `src/asy_dns_client.py:161`, `src/asy_ntp_client.py:265`.
- `RegionBuffer`: `src/asy_uart_comm.py:343-344`, and `FRAMChunk`/`FRAMTimestampedChunk.get_buffer()`
  (`src/asy_fram_manager.py:483`, `:549-551`). Those are the only builders of its two subclasses.
- `FramingCOBS`: no product builder at all. Neither codegen (`buildgen/codegen.py:186`) nor `src/` builds one, so this
  part is vacuous.
- UART bus: `UARTComm.__init__` sets `uart.logger` (`src/asy_uart_comm.py:212-213`) before `_allocate()` (`:247`). The
  bus's own construction reaches `deinit()` only with `_uart` None, which returns before any report
  (`src/asy_uart_driver.py:423-424`, `:468`). Every generated UART bus has its `uart_link`.
- The effect is still construction-time silence (claim 2).

### 4. `err_nomem()` allocates nothing on a full heap and cannot raise there: STANDS
- `b1f_probe2` P4: with the heap locked and a MemoryError born under the lock, levels 0 and 1, and on a really full heap
  (failing a 64 KiB allocation), it raised nothing ("P4 raised: [None, None, None]") and printed its lines.
- `b1f_full2`: it recorded the overflow on a full heap.
- Only a pending KeyboardInterrupt delivered inside print's write path could still raise, which has nothing to do with the
  heap.

### 5. E28 only for a store unreadable at setup: STANDS
- The only use of `_ERR_LOG_RAM_ONLY` is `src/asy_print_log.py:388`, in `setup()` when `_read()` is None.
- No other `_ERR_*` constant holds 28.
- Every `errno=` expression in `src/` and the generated modules is an `_ERR_` name or a forwarded constant.

### 6. A pre-setup entry can only come from a construction fault: STANDS
- History entries come only from the async `err_s`/`wrn_s`.
- Every `setup()` calls `pr.setup()` first.
- During the boot setup batch the only task running is `main`, so no other task can log meanwhile.
- One unreachable window: an entry made while a logger's own setup read is in flight would be overwritten by the restore
  (`src/asy_print_log.py:390-393`). See "Outside the claims".

### 7. Concurrent ResetErrors on one logger: STANDS
- `_put_status` takes no lock (`src/asy_webserver_service.py:844-874`, no Lock anywhere in the module).
- Each connection is its own task (max_connections 6), and `gather` yields during the store write, so two PUTs overlap.
- The per-reset bits handle the overlap (`src/asy_print_log.py:346-376`).

### 8. Nobody read `set_level()`'s bool; the clamp changes no answer: STANDS
- Product callers: `_apply_level` discards the result (`src/asy_system_service.py:276-283`), and so does
  `PrintLog.__init__`.
- DebugLevel is `int 0..5` (`:122`), checked by `type_or_range_error` on the PUT path and read back through `get_int_values`.
- Only a manual REPL `main(debug=9)` now clamps to 5 instead of staying off: console output only.

### 9. The six retired rows have no reader: STANDS
- No literal reference anywhere (git grep of the six numbers and names, `:!arduino :!audit`).
- The website and test texts skip retired rows (`buildgen/definitions.py:302`, `tests/_error_codes.py:20`).
- The only generic reader, `test_a_retired_code_has_no_live_site` (`tests_scripts/test_error_catalog.py:211-223`), now
  checks an empty set. `test_no_code_constant_holds_a_non_catalog_value` (`:477`) covers a reintroduced constant.

### 10. The records removed at base `:474` and `:619` were dead: STANDS
- `:474` is the await of a stopped task, after the supervisor is proven done.
- `:619` is inside the supervisor's own top handler, after its loop has ended.
- The supervisor is the only reader of the record (`src/asy_system_service.py:551`) and is never restarted (`:797-804`).
- At `:619` the head's `err_s` records anyway.

### 11. No product check got weaker: REFUTED (narrow)
- `test_fatal_report_sites.py` stopped covering `_shutdown_sequence`'s outer handler, which was covered at `4516e60e`
  (where only `report_unretrieved` was exempt). Plant 1 in `b1f_plant` passes.
- Its new `_logs` also accepts a qualifying log after an early return (plant 2). Neither change is needed for claim 1's item.
- Honest severity: low today. The supervisor reads nothing after a command passes the gate, so that outer handler's record
  is unreadable too.
- Everything else I checked follows mechanically from items 1, 2, 5, 6 or 8:
  - every removed test in `tests/test_asy_print_log.py`
  - `test_task_tops.py`, which drops `_reports`
  - `test_readiness_gates.py`
  - the LOG_RAM_ONLY expectations in `test_fram_integration.py`, `test_digital_twin_fram*.py`, `test_asy_system_service.py`
    and `test_serving_heap_at_default_gc.py`
  - the boot entry's `console` line
- The removed `test_a_reset_whose_write_waits_behind_setups_read_...` pinned a window that product cannot reach (below).

### 12. Numbers: STANDS
- `b1f_sizes` (`S/u35r/r1/B1/b1f_out/head.tsv` against `S/u35r/r0/mpy/now.tsv`): 207,188 B in total, −1,520 B.
- `now.tsv` equals `4516e60e` byte for byte (`b1f_out/base.tsv`).
- Exactly three modules grew: `asy_framing_codecs.py` +105, `asy_uart_driver.py` +81, `asy_udp_socket.py` +20. Each
  growth is the logger parameter or attribute, its forwarding method and, in the codec, the TYPE_CHECKING import block for
  its annotation.

## Outside the claims
- (a) Exhausted heap plus C-stack overflow: a loss in the product itself (claim 1, first point). The fixed-arity
  `err_nomem` shape already shows how to record without allocating.
- (b) Every no-autostart boot entry prints its start line at import, at any level (`buildgen/codegen.py:848`). It is a
  manual build, but "level 0 prints nothing" does not hold for it.
- (c) Read only, not run: if a `reset()` ever ran during a logger's setup read, setup's restore
  (`src/asy_print_log.py:390-393`) would put the stored ring back over it. The reset would then persist a slot stored
  before it began and drop the entry that arrived after. Product cannot reach this: the webserver starts only after the
  setup batch.
