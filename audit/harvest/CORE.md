# Harvest — CORE: Core runtime modules

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`, moved to `4dc80ef` by V11).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 48, INVAR 61, MIRROR 3, LIMIT 36, RISK 30, ASSUME 33, PLATFORM 2, WORKAROUND 2, SUPPRESS 30, TODO 11, OPENQ 4, DRIFT 5, NOTE 4 — 269 items.


## src/api_response.py

- **CORE.N001** SUPPRESS · `src/api_response.py:10-13` — "except ImportError: # typing has no runtime
  presence on MicroPython" — `typing` import failure swallowed to `TYPE_CHECKING = False` (repo-wide
  idiom; recorded per shipped site). · [H01]
- **CORE.N002** INVAR · `src/api_response.py:24-29` — "Structural stand-in for microdot.Request ...
  Shared with asy_webserver_service.py" — `_RequestLike` Protocol models only `.json` of vendored
  Microdot's Request; imported by `asy_webserver_service.py:28`; must track `ext/microdot.py` by hand
  (mypy never sees the real class). · [H01]
- **CORE.N003** INVAR · `src/api_response.py:31-34` — "it must not collide with any driver's own
  numbering or with base_classes.py's reserved 1-9 - hence a fixed out-of-range sentinel" — errno 99 is
  logged into the caller's `.pr`; uniqueness is by convention (C.7.1 map, SPECIFICATION.md:1940); note
  `FRAM_SPI` also uses errno 99 (`src/asy_fram_driver.py:302`) on its own logger. · related: XCUT.T07 ·
  [H01]
- **CORE.N004** ASSUME · `src/api_response.py:51-52` — "code == 0 is the only \"OK\" outcome (matches
  every existing endpoint's convention)" — Unverified claim that every endpoint uses 0 as sole OK. ·
  related: CORE.T07 · [H01]
- **CORE.N005** SUPPRESS · `src/api_response.py:69-71` — "except Exception: # request.json has no
  internal guarding (see CLAUDE.md)" — Any exception from `request.json` swallowed to `None` → code 1. ·
  related: CORE.S14 · [H01]
- **CORE.N006** INVAR · `src/api_response.py:89-91` — "The post-write hook fires at most once per call,
  only if a field actually changed." — "changed" is implemented as any status == "Valid" (:94); relies
  on `_set_dict_cfg` never reporting "Valid" for an unchanged field. · related: XCUT.T11 · [H01]
- **CORE.N007** ASSUME · `src/api_response.py:100-103` — "what reaches here is almost always a
  caller-supplied post_fct/post_asy_fct raising" — Broad catch also covers `_set_dict_cfg` failures;
  result is code 100 with empty `result` even after fields were persisted. · covered-by: CORE.S06 ·
  [H01]
- **CORE.N008** SUPPRESS · `src/api_response.py:100-105` — "except Exception as e: ... err_s(\"Unhandled
  error in setter dispatch:\", e, errno=_ERRNO_UNHANDLED_DISPATCH)" — Every exception in
  dispatch/post-hook is swallowed into a persisted errno 99 + code 100 envelope. · related: CORE.S06 ·
  [H01]
- **CORE.N009** LIMIT · `src/api_response.py:104` — err_s "Unhandled error in setter dispatch:" — Log
  string declaring the "unexpected" defense-in-depth case (persisted, errno 99). · related: CORE.S06 ·
  [H01]

## src/asy_fram_manager.py

- **CORE.N010** INVAR · `src/asy_fram_manager.py:731` — "await self.pr.setup() # required for all logged
  warnings and errors" — Logger must be set up before any persisted log (same idiom in every driver's
  init). · related: XCUT.T08 · [H01]

## src/base_classes.py

- **CORE.N011** INVAR · `src/base_classes.py:3` — "Every method returns a well-defined value, never
  raises." — Module-wide never-raise contract upheld by broad catches · related: CORE.T09 · [H02]
- **CORE.N012** INVAR · `src/base_classes.py:5-7` — "`__init__` never calls `self.pr.setup()` (sync vs.
  async) - the caller's async setup must, or FRAM persistence stays inert." — Logger setup is every
  owner's obligation; nothing enforces it · related: XCUT.T08 · [H02]
- **CORE.N013** SUPPRESS · `src/base_classes.py:16` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **CORE.N014** SUPPRESS · `src/base_classes.py:49-50` — "except RuntimeError: # in case it's already
  released somehow / pass" — Double release silently swallowed · covered-by: CORE.S13 · [H02]
- **CORE.N015** INVAR · `src/base_classes.py:85-88` — "A negative max_val is a dev-time-typo risk, never
  a real call-site input - clamped to 0" — Silent clamping instead of rejection (also `set_value`
  clamps, relied on by PauseTime/backlog) · related: CORE.T08 · [H02]
- **CORE.N016** ASSUME · `src/base_classes.py:171-172` — "self.name = resolved_name # matches
  self.pr.name - the _ModuleLike registration shape" — Not true in the `logger=` reach-through branch ·
  covered-by: CORE.S13 · [H02]
- **CORE.N017** SUPPRESS · `src/base_classes.py:194-201` — "except Exception as e: # subclass override
  could legitimately misbehave; not statically ruled out ... errno=3" — Broad catch, persisted; wrnno 2
  "Sensor config manager adds unknown keys to config dict!" persists on every GET while the condition
  holds · [H02]
- **CORE.N018** SUPPRESS · `src/base_classes.py:204-210` — "except Exception as e: # callback is
  caller-supplied; its runtime behavior isn't statically known ... errno=4" — Broad catch, persisted;
  wrnno 1 ("callback adds unknown keys") per GET, no `repeat=` · [H02]
- **CORE.N019** RISK · `src/base_classes.py:219-229` — "await self.pr.err_s(\"Error counter increased
  to\", self._err_cnt_internal, errno=1)" — Every failed read cycle persists errno 1, then errno 2 and a
  task restart that resets the streak — a dead sensor writes to the FRAM ring continuously · related:
  PERF.T10 · [H02]
- **CORE.N020** INVAR · `src/base_classes.py:233-235` — "every module the generated
  _collect_error_sources() reaches implements this structurally, no shared base required" — Duck-typed
  fan-in contract checked only by mypy/tests · related: XCUT.T07 · [H02]
- **CORE.N021** INVAR · `src/base_classes.py:244-246` — "_err_cnt_internal ... must not survive a reset
  the caller expects to be total" — Reset semantics contract · [H02]
- **CORE.N022** INVAR · `src/base_classes.py:274-276` — "Never the raw `name`, which is the type's base
  name." — Config filename/logger naming depends on `instance_name()` · related: CORE.T12 · [H02]
- **CORE.N023** LIMIT · `src/base_classes.py:305-308` — "Pre-write values are snapshotted for
  _recover_failed_push, filtered to persisted keys" — No per-module serialization of snapshot → persist
  → push → recover · covered-by: CORE.S05 · [H02]
- **CORE.N024** SUPPRESS · `src/base_classes.py:309-313` — "except Exception as e: await
  self.pr.err_s(\"Error reading previous config for fallback:\", e, errno=7)" — Broad catch, persisted;
  recovery then falls back to defaults · [H02]
- **CORE.N025** SUPPRESS · `src/base_classes.py:317-324` — "except Exception as e: await
  self.pr.err_s(\"Error writing config dict:\", e, errno=5)" — Broad catch, persisted; whole request
  reported "Failed" · [H02]
- **CORE.N026** INVAR · `src/base_classes.py:327-330` — "every requested key is \"Failed\", not
  \"Invalid\" (which would misleadingly suggest the values themselves were the problem)" —
  Invalid-vs-Failed semantics (H.6) · related: REST.S10 · [H02]
- **CORE.N027** ASSUME · `src/base_classes.py:333-336` — "a misbehaving _set_mgr_cfg override could
  report persisted=True but omit a key from results (the real ConfigManager-backed path never does)" —
  Defensive default relies on a stated property of ConfigManager (low) · [H02]
- **CORE.N028** INVAR · `src/base_classes.py:344-349` — "Push the coerced value that was actually
  persisted, not the caller's raw pre-coercion one" — C.5.2 push contract; `schema_dict()` rebuilt per
  field · related: MEM.T08 · [H02]
- **CORE.N029** SUPPRESS · `src/base_classes.py:352-354` — "except Exception as e: # callback is
  caller-supplied... errno=6" — Broad catch → Failed + recovery chain · [H02]
- **CORE.N030** INVAR · `src/base_classes.py:366-368` — "written back through _set_mgr_cfg only,
  bypassing _push_callbacks so a failing push can't loop" — Recovery persists a value the hardware may
  not hold (config ↔ chip divergence) · related: XCUT.T11 · [H02]
- **CORE.N031** ASSUME · `src/base_classes.py:371` — "return # shouldn't happen - key was already
  validated against cfg_vals above" — Unreachable-by-reasoning branch (low) · [H02]
- **CORE.N032** SUPPRESS · `src/base_classes.py:382-384` — "except Exception as e: # getter is
  caller-supplied... errno=8" — Broad catch, persisted · [H02]
- **CORE.N033** LIMIT · `src/base_classes.py:394-397` — "await self._set_mgr_cfg({key: recovered},
  cfg_vals) / except Exception as e: ... errno=9" — The recovery write's `(persisted, results)` return
  is discarded; a non-raising failed recovery is silent · related: CORE.T04 · [H02]

## src/config_manager.py

- **CORE.N034** INVAR · `src/config_manager.py:3` — "Every public function/method returns a documented
  \"invalid\" sentinel, never raises." — Never-raise contract via broad catches · related: CORE.T03 ·
  [H02]
- **CORE.N035** SUPPRESS · `src/config_manager.py:15` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **CORE.N036** SUPPRESS · `src/config_manager.py:82-83, 96-97` — "except Exception: return []" /
  "except Exception: return {}" — Malformed schema silently becomes empty · related: CORE.T03 · [H02]
- **CORE.N037** LIMIT · `src/config_manager.py:93` — "duplicate names keep the last occurrence" —
  Duplicate schema field names silently collapse · [H02]
- **CORE.N038** SUPPRESS · `src/config_manager.py:113-114, 117-118` — "except Exception: return {}" /
  "except Exception: return {name: dict.fromkeys(fields)}" — Namedtuple introspection failures degrade
  silently to empty/None values · [H02]
- **CORE.N039** DRIFT · `src/config_manager.py:126-127` — "the generated lightCmdLED dispatch has no
  FieldSchema to hand type_or_range_error(), so it calls this" — Codegen calls `type_or_range_error()`
  with synthetic schemas instead · covered-by: CORE.S15 · [H02]
- **CORE.N040** RISK · `src/config_manager.py:131-133` — "No exact-round-trip check on this direction...
  an accepted gap... past 2**24 on the real single-precision build... the largest today is 5000.0" —
  Accepted precision gap resting on a current-schema maximum that no check pins · related: CORE.T03 ·
  [H02]
- **CORE.N041** SUPPRESS · `src/config_manager.py:185-186` — "except Exception: pass" — Any validation
  exception → "invalid" · [H02]
- **CORE.N042** SUPPRESS · `src/config_manager.py:205-206` — "except Exception: # malformed field record
  / return True, None" — Malformed field → no default · [H02]
- **CORE.N043** INVAR · `src/config_manager.py:228-230, 235-237` — "write_config() always stages a full
  snapshot... so a plain swap - not a per-key merge - is correct here" — Read-your-write correctness
  depends on full-snapshot staging · related: CORE.T02 · [H02]
- **CORE.N044** RISK · `src/config_manager.py:241-243, 271-273` — "await self.pr.err_s(self.config_file,
  \"- Config is not valid, cannot read!\", errno=5)" — An invalid config persists an error on every read
  (errno 5/7), no `repeat=` · related: CORE.T01 · [H02]
- **CORE.N045** LIMIT · `src/config_manager.py:256-259` — "return [converter(v) for v in values]" —
  `get_int_values()` uses `int()`, silently truncating/converting · covered-by: CORE.S12 · [H02]
- **CORE.N046** INVAR · `src/config_manager.py:268-270` — "No lock needed: neither write_config() nor
  _flush_staged() awaits mid-mutation of the field this reads" — Lock-free read justified by the absence
  of awaits mid-mutation · related: CORE.T08 · [H02]
- **CORE.N047** RISK · `src/config_manager.py:319, 330` — "\"- Key\", key, \"not found, skipping!\",
  errno=10" / "\"- Type / range error in\", key, \"- skipping!\", errno=12" — Client input errors
  persisted in the fault ring · covered-by: CORE.S11 · [H02]
- **CORE.N048** LIMIT · `src/config_manager.py:323-325` — "\"- Default Key\", key, \"Error or None, no
  data written!\", errno=11 / return False, {}" — One bad default aborts the whole write and drops the
  per-key results already computed · related: CORE.T02 · [H02]
- **CORE.N049** ASSUME · `src/config_manager.py:338-341` — "\"- Key\", key, \"not found in config file,
  ignoring!\", errno=13" — Path unreachable after a valid `setup()` by reasoning (low) · [H02]
- **CORE.N050** RISK · `src/config_manager.py:353-360` — "self._staged = new_cache / self._pending_flush
  = asyncio.create_task(self._flush_staged(new_cache))" — Staging before `create_task`; MemoryError
  there leaves staged-but-never-flushed state · covered-by: CORE.S17 · [H02] ⟨quote not matched at the
  anchor⟩
- **CORE.N051** INVAR · `src/config_manager.py:365-367` — "It re-acquires write_config()'s own lock, so
  at most one write is in flight per ConfigManager" — Per-instance serialization only; two
  ConfigManagers can flush concurrently · related: CORE.T02 · [H02]
- **CORE.N052** SUPPRESS · `src/config_manager.py:378-380` — "except (MemoryError, OSError, ValueError,
  AttributeError) as e: # ... logged, never re-raised, and never retried here. ... \"running
  unpersisted\"" — Degraded mode: value live, not on flash (errno 14) · covered-by: CORE.T02 · [H02]
- **CORE.N053** SETTLED · `src/config_manager.py:382-384` — "The validated value stays in effect whether
  or not the write landed... only persistence failed (SPECIFICATION.md C.7.3)." — `_cache` committed in
  `finally` after a failed write · covered-by: CORE.T02 · [H02]
- **CORE.N054** RISK · `src/config_manager.py:391-400` — "Only ever holds the LATEST call's task...
  pending = self._pending_flush / await pending" — Unguarded await of the flush task before reboot ·
  covered-by: CORE.S09 · [H02] ⟨quote not matched at the anchor⟩
- **CORE.N055** INVAR · `src/config_manager.py:403-405` — "without it self.pr.initialized never becomes
  True and each later err_s()/wrn_s() silently skips its own FRAM write" — Logger setup obligation ·
  related: XCUT.T08 · [H02]
- **CORE.N056** RISK · `src/config_manager.py:423-426` — "except (MemoryError, OSError, TypeError) as e:
  # missing/unreadable file... same \"degrade, don't propagate\" treatment" — Any read failure (incl.
  transient EIO/MemoryError) → wrnno 3 "not found" → file rewritten with defaults · covered-by: CORE.S02
  · [H02]
- **CORE.N057** RISK · `src/config_manager.py:461-463` — "await self.pr.wrn_s(self.config_file, \"-
  Removed invalid keys from config file!\", wrnno=5)" — Keys not in the constructed schema are dropped
  on rewrite (SPECIFICATION.md:1722-1725 "real operational hazard"; firmware that renames/removes a
  field loses it) · related: CORE.T12 · [H02]
- **CORE.N058** SETTLED · `src/config_manager.py:479-485` — "One attempt per setup(), never retried
  (C.7.3)... a failed write costs persistence, never the config - refusing it ended every reader's task
  and looped the device through reboots" — Boot-time write failure runs unpersisted by design · related:
  CORE.T12 · [H02]

## src/print_log.py

- **CORE.N059** INVAR · `src/print_log.py:3` — "Every method returns a well-defined value, never raises
  - PrintLogHistoryStore's FRAM calls are wrapped broadly" — Never-raise contract via broad catches
  around FRAM · related: CORE.T05 · [H02]
- **CORE.N060** SUPPRESS · `src/print_log.py:15` — "except ImportError: # typing has no runtime presence
  on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **CORE.N061** INVAR · `src/print_log.py:38-40` — "avoiding a real runtime import cycle (it imports
  PrintLogHistory from here)" — Import-graph constraint: `print_log.py` must never import
  `asy_fram_manager` at runtime · related: XCUT.T16 · [H02]
- **CORE.N062** INVAR · `src/print_log.py:61-64` — "_NO_ERR = const(0x00) / _MAX_ERR = const(0x7F) /
  _NO_WRN = const(0x80) / _MAX_WRN = const(0xFF)" — One-byte encoding caps every errno/wrnno at 127
  (dynamic supervisor wrnno must stay ≤127) · related: XCUT.S07 · [H02] ⟨quote not matched at the
  anchor⟩
- **CORE.N063** WORKAROUND · `src/print_log.py:109-111` — "no non-Any element type can satisfy that
  overload set (PEP 692's Unpack needs 3.11, and typings/'s own typing.pyi declares TypedDict as a bare
  object)" — `**kwargs: Any` works around stub/typing limits; removal trigger none stated · related:
  PLAT.T05 · [H02]
- **CORE.N064** LIMIT · `src/print_log.py:112-114` — "def err(self, *args: object, **kwargs: \"Any\") ->
  None: if self.level >= _LOG_ERR: print(...)" — Sync `err()` neither counts nor persists (vs C.7.1
  "still counts it" for repeats) · covered-by: UART.S01 · [H02]
- **CORE.N065** LIMIT · `src/print_log.py:154-156` — "internal-failure prints, gated on any logging
  being enabled at all" — FRAM write failures inside the logging layer are invisible at level 0 ·
  covered-by: XCUT.T24 · [H02]
- **CORE.N066** LIMIT · `src/print_log.py:161-166` — "if self.err_count < _MAX_CNT: self.err_count += 1
  ... if errno <= _NO_ERR: return" — Count saturates at 0xFFFF; `errno=0` counts but never persists ·
  covered-by: CORE.S13 · [H02]
- **CORE.N067** INVAR · `src/print_log.py:167` — "a repeat is counted and written, but spends no slot -
  SPECIFICATION.md Part C.7.1" — Repeat semantics every caller's dedupe relies on · related: XCUT.T07 ·
  [H02]
- **CORE.N068** LIMIT · `src/print_log.py:171-172` — "self._diag(\"PrintLog: Error number\", errno -
  min_e, \"is invalid!\")" — An out-of-range code is counted and written but leaves no history entry,
  reported only at level > 0 · related: XCUT.T07 · [H02]
- **CORE.N069** RISK · `src/print_log.py:173-176` — "Return regardless of logging level - don't write
  stale state to FRAM before setup()." — Pre-setup entries live in RAM only and are overwritten when
  `setup()` restores the FRAM ring · covered-by: CORE.S03 · [H02]
- **CORE.N070** DRIFT · `src/print_log.py:181-183, 189-191` — "0x00/0x80 are \"nothing recorded\"" — Raw
  0x80 reported as ErrNum 128 rather than 0 · covered-by: CORE.S13 · [H02]
- **CORE.N071** RISK · `src/print_log.py:213-223` — "No `not self.initialized` guard here, unlike
  _store_err(): a cleared ring is exactly what the caller asked to persist" — `reset()` racing an
  in-flight `setup()` read · covered-by: CORE.S04 · [H02]
- **CORE.N072** SUPPRESS · `src/print_log.py:236-240` — "try: # broad on purpose: defense-in-depth
  against the Protocol in the abstract... except Exception: self.fram = None" — Chunk allocation failure
  → RAM-only logger, reported only via `_diag` · related: XCUT.T24 · [H02]
- **CORE.N073** SUPPRESS · `src/print_log.py:247-255` — "except Exception: return False" — FRAM write
  failures swallowed (then `_diag`, silent at level 0) · related: XCUT.T24 · [H02]
- **CORE.N074** SUPPRESS · `src/print_log.py:260-269` — "except Exception: return False" — Any read
  failure indistinguishable from "never written" · covered-by: CORE.T11 · [H02]

## src/system_service.py

- **CORE.N075** INVAR · `src/system_service.py:2` — "Every method returns a well-defined value, never
  raises." — Never-raise contract · related: CORE.T09 · [H02]
- **CORE.N076** SETTLED · `src/system_service.py:4-6` — "The real reset
  reboot_system()/reboot_bootloader() take after _RESET_DELAY is the intent, not a failure." —
  Deliberate delayed reset · related: XCUT.T13 · [H02]
- **CORE.N077** SUPPRESS · `src/system_service.py:24` — "except ImportError: # typing has no runtime
  presence on MicroPython" — Swallowed ImportError for `typing` · [H02]
- **CORE.N078** ASSUME · `src/system_service.py:42` — "_NTP_WAIT_TIME = const(120) # 2 mins until random
  boot signature is used" — Boot-signature fallback window · related: CORE.T06 · [H02]
- **CORE.N079** MIRROR · `src/system_service.py:57-60` — "range matches print_log.py's
  PrintLog.level_off()..level_info() (0-5); default 0 matches the reference file's own debug=False." —
  DebugLevel bounds duplicate `print_log.py`'s level constants; default claims legacy parity · related:
  CORE.S08 · [H02]
- **CORE.N080** SETTLED · `src/system_service.py:98-100` — "deliberately not a SensorReaderConfig
  subclass" — Design decision (duck-typed fan-in) · [H02]
- **CORE.N081** SUPPRESS · `src/system_service.py:136-139` — "except Exception as e: # caller-supplied
  callback, typed as any Callable - guarded broadly ... errno=1" — Broad catch, persisted — once per
  second until synced if the callback keeps raising · [H02]
- **CORE.N082** SUPPRESS · `src/system_service.py:232` — "if tasks[n] is None or tasks[n].done(): #
  type: ignore[union-attr]" — mypy suppression in shipped code · [H02]
- **CORE.N083** SUPPRESS · `src/system_service.py:234` — "await self._log_dead_task(tasks[n], n) # type:
  ignore[arg-type]" — mypy suppression in shipped code · [H02]
- **CORE.N084** LIMIT · `src/system_service.py:292-296` — "level = await
  self.cfgmgr.get_int_values(self.cfg_schema) / if level is None: return" — Invalid system config
  silently keeps constructor debug levels · covered-by: CORE.S08 · [H02]
- **CORE.N085** SUPPRESS · `src/system_service.py:335-338` — "except Exception as e: await
  self.pr.err_s(\"Level setter failed:\", e, errno=7)" — Broad catch per setter, persisted · [H02]
- **CORE.N086** SUPPRESS · `src/system_service.py:363` — "storage_pause = self.storage_pause # local
  capture: mypy can't narrow a closed-over self attribute" — Typing workaround (no suppression comment,
  low) · [H02]
- **CORE.N087** RISK · `src/system_service.py:375-394` — "await self.uptime.set_value(0) / await
  self.boot_signature.set_value(None)" — A supervisor restart of this task fakes a reboot; uptime counts
  wake-ups · covered-by: CORE.S01 · [H02] ⟨quote not matched at the anchor⟩

## tests/_sensortask_scenarios.py

- **CORE.N088** SETTLED · `tests/_sensortask_scenarios.py:690-692` — "owner requirement: system-wide,
  but no shared mutable value" — debug-level registry design (Part A.7) · [H03]
- **CORE.N089** RISK · `tests/_sensortask_scenarios.py:966-968` — "unlike the accepted power-loss
  residual risk (Part F.2), this path can wait the flush out" — power loss with a staged config write is
  an accepted residual risk · [H03]

## tests/test_api_response.py

- **CORE.N090** SETTLED · `tests/test_api_response.py:112-113` — "Final project decision: per-field
  failures don't demote the overall response" — partial failures stay `res: OK, code: 0` · related:
  CORE.T07 · [H03]
- **CORE.N091** SETTLED · `tests/test_api_response.py:181-183` — "with its own try/except as
  defense-in-depth on top of Microdot's own blanket per-request catch (project decision, based on prior
  field experience" — `handle_set_cmd`'s own wrapper is a deliberate decision · related: CORE.T07 ·
  [H03]
- **CORE.N092** ASSUME · `tests/test_api_response.py:283-329` — "Pins that order as real behaviour, and
  confirms the response still degrades into the same generic envelope." — tests pin current behaviour: a
  raising post-hook (after fields were persisted) yields `ERR`/code 100 with an empty `result`, and a
  sync `post_fct` raising means the async hook never runs · covered-by: CORE.S06 · [H03]
- **CORE.N093** SETTLED · `tests/test_api_response.py:336-337` — "A whole-operation persistence failure
  is per-field detail (\"Failed\" in result), not a top-level protocol error" — persistence failure
  returns an OK envelope · related: CORE.T07 · [H03]

## tests/test_asy_bmp3xx_driver.py

- **CORE.N094** INVAR · `tests/test_asy_bmp3xx_driver.py:1477-1479` — "PrintLogHistoryStore.setup() is a
  no-op until initialized, so a logged error before setup() would never actually persist" — `pr.setup()`
  must run first in every `_init_*()` · related: CORE.S03, XCUT.T08 · [H03]
- **CORE.N095** SETTLED · `tests/test_asy_bmp3xx_driver.py:2042-2044` — "Now it initialises on the
  validated defaults and the write is not retried." — C.7.3: a failed config write costs persistence,
  not the config; no retry · related: CORE.T01, XCUT.T10 · [H03]

## tests/test_asy_fram_driver.py

- **CORE.N096** PLATFORM · `tests/test_asy_fram_driver.py:1003,1015,1030` — "wrn_s()'s history entries
  are offset by _NO_WRN (0x80)" — persisted warning-number encoding · related: XCUT.T07 · [H03]
- **CORE.N097** RISK · `tests/test_asy_fram_driver.py:1378-1379` — "Same tolerance Lockable's own
  __aexit__ has, applied to the inner lock." — double release is tolerated (swallowed) on the inner lock
  too · related: CORE.S13 · [H03]

## tests/test_asy_i2c_driver.py

- **CORE.N098** RISK · `tests/test_asy_i2c_driver.py:794-797` — "__aexit__'s own release() must swallow
  the resulting RuntimeError, not propagate it" — double release is tolerated silently · related:
  CORE.S13 · [H03]

## tests/test_asy_isl29125_driver.py

- **CORE.N099** RISK · `tests/test_asy_isl29125_driver.py:1661-1662` — "_get_dict_cfg() warns (wrnno=1)
  on any key the schema does not carry, so a typo here would log a warning on every GET /sensors" — a
  schema/key mismatch floods the persisted warning history on every GET · related: CORE.S11 · [H03]
- **CORE.N100** LIMIT · `tests/test_asy_isl29125_driver.py:1687-1688` — "that outer guard skips the
  whole dict update and leaves the fields showing persisted values as if they were live" — base-class
  `_get_dict_cfg()` failure shows persisted values as live (applies to other drivers relying on the
  outer guard) · related: SENS.T16 · [H03]
- **CORE.N101** LIMIT · `tests/test_asy_isl29125_driver.py:1741` — "ConfigManager.get_dict() is
  all-or-nothing and would KeyError on a key it never persisted" — ConfigManager API limit · related:
  CORE.T12 · [H03]
- **CORE.N102** SETTLED · `tests/test_asy_isl29125_driver.py:1766-1767` — "_recover_failed_push() skips
  a command-only field by design" — recovery chain excludes command-only fields · [H03]

## tests/test_asy_neopixel_driver.py

- **CORE.N103** INVAR · `tests/test_asy_neopixel_driver.py:498-499` — "FRAM persistence is inert until
  setup() runs - matches every other module's real main-loop convention" — `pr.setup()` ordering
  convention · related: XCUT.T08 · [H03]

## tests/test_asy_ntp_client.py

- **CORE.N104** INVAR · `tests/test_asy_ntp_client.py:1995,2389,2404` — "C.7.1's repeat rule: a dead
  server would otherwise fill the ten-slot ring with one code." — one error-ring slot per distinct code
  per failure episode; errno and wrnno with equal numbers must never suppress each other · [H04]
- **CORE.N105** PLATFORM · `tests/test_asy_ntp_client.py:115-117` — "its os.stat() 0x4000 (MP_S_IFDIR)
  check rejects it and leaves self.valid False" — ConfigManager's invalid-state path depends on the
  MicroPython stat mode bit 0x4000 for directories · - (low) · [H04]

## tests/test_asy_sgp40_driver.py

- **CORE.N106** SETTLED · `tests/test_asy_sgp40_driver.py:599` — "decremented by the success, not reset
  to 0" — error-streak counter decrements on success rather than resetting · - (low) · [H04]
- **CORE.N107** INVAR · `tests/test_asy_sgp40_driver.py:623-625` — "the wrapper must not forward its
  False-means-no-op return as a False-means-push-failed result" — push-callback wrappers must translate
  a setter's no-op False, else `_set_dict_cfg` reports "Failed" and runs recovery; convention per driver
  · related: XCUT.T11 · [H04]
- **CORE.N108** ASSUME · `tests/test_asy_sgp40_driver.py:632-634` — "_set_dict_cfg only ever invokes a
  push callback with an already schema-validated value ... defense-in-depth" — push callbacks rely on
  the caller having validated types · - (low) · [H04]
- **CORE.N109** SETTLED · `tests/test_asy_sgp40_driver.py:642-644,656-658` — "its special-alone shape
  (def=None, special=True) means ConfigManager never stores it" — `SGPResetVOC` is a command-only field:
  never persisted, always reported "Valid", repeated value re-triggers the reset · [H04]
- **CORE.N110** INVAR · `tests/test_asy_sgp40_driver.py:683-685` — "ConfigManager.get_dict() is
  all-or-nothing on a key never in _cache" — get_dict_cfg() must pass a schema excluding SGPResetVOC;
  including a never-cached key would fail the whole read · [H04]
- **CORE.N111** SETTLED · `tests/test_asy_sgp40_driver.py:2409-2410` — "Regression (SPECIFICATION.md
  C.7.3): the failed write used to surface here as errno 12 and a task restart per boot" — an unwritable
  config file now runs on validated defaults (logged as CFGMGR errno 4) · [H04]

## tests/test_asy_uart_driver.py

- **CORE.N112** SUPPRESS · `tests/test_asy_uart_driver.py:1296-1299` — "__aexit__'s own release() must
  swallow the resulting RuntimeError, not propagate it" — Lockable `__aexit__` swallows a double-release
  RuntimeError · - (low) · [H04]

## tests/test_asy_webserver_service.py

- **CORE.N113** ASSUME · `tests/test_asy_webserver_service.py:2923-2924` — "ConfigManager's own
  asyncio.Lock already rules out a data race (SPECIFICATION.md Part C.7)" — concurrent GET + PUT test
  relies on ConfigManager's lock · - (low) · [H04]

## tests/test_asy_wifi_service.py

- **CORE.N114** SETTLED · `tests/test_asy_wifi_service.py:649-651` — "Project-wide decision: every
  setter returns bool (True = applied), not None." — uniform setter return contract · related: SENS.T08
  (low) · [H04]
- **CORE.N115** SETTLED · `tests/test_asy_wifi_service.py:687-688,698-704` — "registered once at
  construction (project decision), not passed per-call" — push callbacks registered at construction;
  only LedWifiOn has one; `set_ext_led()` is REST-unreachable and unregistered · - (low) · [H04]
- **CORE.N116** SETTLED · `tests/test_asy_wifi_service.py:1504-1506` — "The episode rule is per distinct
  code, not per episode as asy_uart_comm.py's own _episode_wrn() is" — WiFi and UART deliberately apply
  different C.7.1 dedupe granularity (per distinct code vs per episode) · related: XCUT.T07 · [H04]

## tests/test_base_classes.py

- **CORE.N117** ASSUME · `tests/test_base_classes.py:344-346` — "A negative max_val is a dev-time-typo
  risk, never a runtime-computed value" — LockedCounter clamps a negative max_val to 0, justified by the
  assumption that max_val is never computed at runtime · [H05]
- **CORE.N118** LIMIT · `tests/test_base_classes.py:389-390` — "LockedValue does no range clamping
  (unlike LockedCounter)" — LockedValue stores NaN/inf and any value untouched; no range guarantee ·
  [H05]
- **CORE.N119** RISK · `tests/test_base_classes.py:1013-1015` — "setup() on a brand-new config file
  already records one wrn_s() ("Config file ... not found")" — Every first boot records a persisted
  (`_s`) FRAM warning for a routine missing-file condition, so a fresh unit's errcount is nonzero by
  design · [H05]
- **CORE.N120** LIMIT · `tests/test_base_classes.py:1019-1021` — ""ok" means "no exception", not "every
  field valid"" — write_config returns (True, ...) for a request whose only key is unrecognized; callers
  must read per-field results, not the flag · [H05]
- **CORE.N121** LIMIT · `tests/test_base_classes.py:1054-1059` — "a repair warning uses
  pr.wrn()/pr.err(), never the persisting _s() variants, so neither logger writes to FRAM" —
  ConfigManager's malformed-file repair is not persisted to the FRAM error log even when FRAM-backed;
  that evidence is lost on reboot · [H05]
- **CORE.N122** SETTLED · `tests/test_base_classes.py:1132-1133` — "Persist-first, then push (project
  decision)" — A value reaches hardware only after it is on flash · [H05]
- **CORE.N123** SETTLED · `tests/test_base_classes.py:1205-1207` — "a failed push triggers
  _recover_failed_push, which corrects the persisted value back" — Failed push → persisted value
  restored via getter / pre-write snapshot / schema default chain; status stays "Failed" · [H05]
- **CORE.N124** INVAR · `tests/test_base_classes.py:1320-1322` — "its return value is not statically
  known to satisfy the field's schema" — A getter's return value used in recovery must pass
  type_or_range_error; an invalid getter value falls to the next rung · [H05]
- **CORE.N125** ASSUME · `tests/test_base_classes.py:1429-1434` — "Real finding (2026-09-08, real bench
  hardware): ... logging one spurious CFGMGR_<name> errno=8 on every single write" — Regression pin for
  a single dated bench finding (special-alone field snapshot fetch); the fix filters the snapshot to
  persisted keys · [H05]
- **CORE.N126** RISK · `tests/test_base_classes.py:1449-1451` — "a fresh special-alone-only schema's own
  setup() legitimately logs two benign warnings" — Two warnings (no config file, no storage values) are
  logged by design for a command-only schema · [H05]
- **CORE.N127** LIMIT · `tests/test_base_classes.py:1493-1495` — "_get_dict_cfg() does no filtering of
  its own, so including Trigger would exercise a separate, pre-existing characteristic" — _get_dict_cfg
  reading a special-alone field is a known, unexplored characteristic the test deliberately steps around
  · [H05]
- **CORE.N128** SETTLED · `tests/test_base_classes.py:1664-1666` — "Final project decision: an
  unrecognized key is just another per-field "Invalid" outcome" — An unknown key does not invalidate the
  rest of a multi-field request · [H05]
- **CORE.N129** SETTLED · `tests/test_base_classes.py:1731-1733` — "every key in the request comes back
  "Failed", not silently dropped or "Invalid"" — An invalid ConfigManager makes every requested key
  report "Failed" · [H05]
- **CORE.N130** SETTLED · `tests/test_base_classes.py:1825-1826` — "Registered once per instance at
  construction time (project decision)" — Push callbacks are per-instance, never shared across instances
  · [H05]

## tests/test_config_manager.py

- **CORE.N131** LIMIT · `tests/test_config_manager.py:130-132` — "Documented, not guarded against:
  nothing in the codebase relies on rejecting this shape" — A bare string passed as a ConfigSchema is
  iterated per character and accepted · [H05]
- **CORE.N132** RISK · `tests/test_config_manager.py:148-150` — "Ambiguous but benign: a single field
  named "" ... returns the same "" a malformed or empty schema does" — name_cfg cannot distinguish an
  empty-named field from a malformed schema; accepted as benign · [H05]
- **CORE.N133** RISK · `tests/test_config_manager.py:347-357` — "Documented, accepted risk: no
  registered float field's bounds go near this range, and this build cannot reproduce the real
  single-precision threshold" — int→float is a blanket accept; float(int) silently rounds beyond the
  mantissa (24 bits on RP2040, 52 on the Unix port); the test proves only the double-precision boundary
  · [H05]
- **CORE.N134** ASSUME · `tests/test_config_manager.py:348-349` — "the largest today is BMP3xx's
  SeaLevelOffs at 5000.0" — The accepted-risk argument rests on a dated survey of float-field bounds; a
  new wide-range float field would invalidate it · [H05]
- **CORE.N135** LIMIT · `tests/test_config_manager.py:477-479` — "A wrong-typed "special" ... makes this
  always return True regardless of check_val - reachable in principle" — type_or_range_error rejects
  everything for a malformed special; only check_cfg_get_default's self-check guards it in practice ·
  [H05]
- **CORE.N136** LIMIT · `tests/test_config_manager.py:661-663` — "An authoring mistake (min/max swapped)
  makes `val_min <= check_val <= val_max` unsatisfiable" — A swapped-bounds schema rejects every value;
  not detected as a schema error by this function (low) · [H05]
- **CORE.N137** SETTLED · `tests/test_config_manager.py:809-811` — "Deliberate, longstanding asymmetry"
  — The bool branch of type_or_range_error never inspects "special"; a wrong-typed bool special surfaces
  only via the self-check · [H05]
- **CORE.N138** ASSUME · `tests/test_config_manager.py:964-966` — "setup()'s `type(coerced_cfg) is not type(new_cfg)`
  check (not `!=`, which 7 != 7.0 would miss)" — setup()'s rewrite trigger compares on type identity;
  the comment's reasoning pins that exact implementation (low) · [H05]
- **CORE.N139** LIMIT · `tests/test_config_manager.py:1201-1206` — "the "123" string key actually on
  disk matches nothing, _cache never being rebuilt from the file after setup()" — A non-string field
  name is never rejected and diverges between _cache and disk · [H05]
- **CORE.N140** LIMIT · `tests/test_config_manager.py:1440-1441, 1524-1526` — "No partial success: the
  loop raises KeyError on the first missing key and the whole call returns None" —
  get_dict/get_int_values are all-or-nothing across fields · [H05]
- **CORE.N141** SETTLED · `tests/test_config_manager.py:1450-1452, 1474` — "Deliberate consequence of
  _cache (see module docstring): get_dict never re-opens the file" — _cache is the sole source of truth
  for reads; out-of-band file deletion/edits have no effect until reboot · [H05]
- **CORE.N142** ASSUME · `tests/test_config_manager.py:1763-1765` — "The "at most one unflushed staged
  value per sensor at a time" assumption WP5's design rests on" — WP5's deferred-flush design assumes at
  most one pending staged value per sensor; the superseded-snapshot check covers back-to-back writes to
  the same key · [H05]
- **CORE.N143** LIMIT · `tests/test_config_manager.py:1775` — "only ever holds the LATEST task - see
  flush_pending()'s own note" — flush_pending() tracks only the most recent flush task · [H05]
- **CORE.N144** SETTLED · `tests/test_config_manager.py:1901-1903` — "A schema self-check failure for
  ANY key hard-aborts the entire call (return False, {})" — Malformed schema → whole write_config
  aborted, no partial write · [H05]
- **CORE.N145** SETTLED · `tests/test_config_manager.py:1932-1934` — "an externally-corrupted file does
  not block a write - it is silently overwritten (repaired) from _cache" — Replaced the pre-cache
  "detect and fail" design · [H05]
- **CORE.N146** SETTLED · `tests/test_config_manager.py:1954-1958` — "The validated value stays in
  effect (C.7.3): its push already reached the module" — A failed deferred flush only logs an errno; the
  read side keeps the new value · [H05]
- **CORE.N147** RISK · `tests/test_config_manager.py:2259-2261` — "open(..., "w") already truncated it
  before json.dump() ran, so a mid-dump failure leaves it unparseable" — A failed flush leaves an
  unparseable config file on flash until the next real change (resubmitting the same value is
  "Unchanged" and writes nothing); the next boot then rebuilds from defaults · [H05]
- **CORE.N148** SETTLED · `tests/test_config_manager.py:2322-2323` — "a failed write costs persistence,
  never the config, and nothing ever retries a write" — C.7.3 write-loop guarantee · [H05]
- **CORE.N149** INVAR · `tests/test_config_manager.py:2530-2541` — "exactly setup()'s and
  _flush_staged()'s opens for writing, and nothing in the module that could re-run one on its own" —
  Enforced by a source-text scan: 2 × `open(self.config_file, "w")`, no Timer/sleep/`while `, exactly
  one `create_task(`; string counting, so a renamed call escapes it · [H05]
- **CORE.N150** INVAR · `tests/test_config_manager.py:2118-2119` — "without config_lock serializing
  them, the second writer overwriting first's read would silently drop one field's update" — Concurrent
  write_config calls rely on config_lock · [H05]
- **CORE.N151** LIMIT · `tests/test_config_manager.py:1119-1121` — "A schema with zero storable fields
  ... init still succeeds and writes an empty {} config file" — A command-only schema still creates a
  config file on flash (low) · [H05]
- **CORE.N152** INVAR · `tests/test_config_manager.py:1223-1225` — "check_cfg_get_default's
  use_value=False path skips popping it, so it's caught and removed by the "unexpected keys remaining"
  cleanup instead" — Two setup() paths must cooperate to purge stale special-only values after a schema
  change · related: CORE.T12 · [H05]
- **CORE.N153** RISK · `tests/test_config_manager.py:2356` — "a missing file's wrnno 3 is routine, not a
  failure" — The routine missing-file warning is persisted and counted on every first boot · [H05]

## tests/test_crc_checks.py

- **CORE.N154** LIMIT · `tests/test_crc_checks.py:629-631` — "if a caller starts feeding a new logical
  buffer via run_inc() without finalizing ... the old bytes are still folded into inc_crc/inc_count" — A
  dangling incremental sequence silently corrupts the next one; callers must always finalize with
  check_inc() · [H05]
- **CORE.N155** INVAR · `tests/test_crc_checks.py:648-649` — "always finalize with check_inc() before
  starting the next one" — Reuse of one CRC instance across sequences is caller discipline;
  non-concurrent use only · [H05]
- **CORE.N156** OPENQ · `tests/test_crc_checks.py:692-694` — "Empty-payload asymmetry between add() and
  check() - flagged, not silently fixed (see PR discussion)" — add() encodes a zero-byte payload that no
  check* method can ever verify; the fix was deferred to a PR discussion not recorded in the docs ·
  [H05]
- **CORE.N157** INVAR · `tests/test_crc_checks.py:707-712` — "Every caller must catch it - see
  asy_uart_driver.py's guarded call sites" — add()/check() are the documented exception to "never
  raises" and propagate MemoryError; every caller must guard (tested in test_asy_uart_driver.py only) ·
  [H05]

## tests/test_notification_scd30_integration.py

- **CORE.N158** INVAR · `tests/test_notification_scd30_integration.py:260-262` — "it only decrements the
  internal consecutive-failure streak (a plain sync pr.err(), not pr.err_s()" — A later success never
  erases persisted history · [H05]

## tests/test_ntp_fram_system_integration.py

- **CORE.N159** SETTLED · `tests/test_ntp_fram_system_integration.py:406-408` — "an unreachable NTP
  server is routine, handled inside the task (Part C.7.2) ... each restart costs 100 of 300 there" — NTP
  failures must never cost supervisor reboot budget; budget numbers (100 of 300) quoted here · [H05]

## tests/test_print_log.py

- **CORE.N160** LIMIT · `tests/test_print_log.py:186-187` — "errno=0 (_NO_ERR, the default) still bumps
  the counter, but _store_err returns before appending anything to history - a real, easy-to-miss
  asymmetry" — err_s() with the default errno counts but leaves no history entry · [H05]
- **CORE.N161** LIMIT · `tests/test_print_log.py:209-210` — "errno=200 pushed past _MAX_ERR (0x7F) once
  _NO_ERR is added - out of the valid error sub-range, so the count still increments but nothing is
  appended" — Out-of-range errnos are counted but invisible in history · [H05]
- **CORE.N162** ASSUME · `tests/test_print_log.py:461-466` — "Regression test for a real bug:
  _store_err()'s "not initialized" guard used to return early only when self.level > _LOG_OFF" — With
  logging off (the production case), a pre-setup err_s() used to overwrite FRAM history; pinned now ·
  related: CORE.T11 · [H05]
- **CORE.N163** SETTLED · `tests/test_print_log.py:477-479` — "SPECIFICATION.md Part C.7: reset()
  deliberately has no "uninitialized" guard" — A reset persists immediately so a later setup() cannot
  restore the old history · [H05]
- **CORE.N164** INVAR · `tests/test_print_log.py:490-492` — "the webserver can answer a ResetErrors PUT
  before that has happened. The reset must survive the setup() that follows it" — Boot window:
  ResetErrors may land before a logger's own pr.setup() · related: CORE.T11 · [H05]
- **CORE.N165** INVAR · `tests/test_print_log.py:512-513` — "claiming initialization on a FAILED write
  would make the later setup() return early, leaving a logger that believes it is persisted and is not"
  — reset() must only mark initialized on a successful write · [H05]

## tests/test_reset_call_site_invariant.py

- **CORE.N166** INVAR · `tests/test_reset_call_site_invariant.py:15-26` — "any other call site would
  bypass storage_pause()/the _RESET_DELAY wait this invariant relies on" — Reset/bootloader confinement
  to system_service.py, enforced by substring scan of `src/` only · covered-by: TEST.S17 · [H05]
- **CORE.N167** DRIFT · `tests/test_reset_call_site_invariant.py:1-3, 30-45` — "WDT() is constructed
  exactly once per sensortask_<device>.py entry point" — `src/` has no `sensortask_*.py` (generated at
  build time), so the exemption branch is dead and "exactly once per entry point" is never asserted; the
  test only checks absence elsewhere in src/ · covered-by: TEST.S17 · [H05]
- **CORE.N168** SETTLED · `tests/test_reset_call_site_invariant.py:30-31` — ""must be hardcoded so no
  error ever can circumvent it when it is set active" - the owner's comment" — Owner decision: WDT
  construction only at each device's entry point · [H05]

## tests/test_system_service.py

- **CORE.N169** SETTLED · `tests/test_system_service.py:194-196, 1053-1055` — "_force_watchdog_starve is
  _reboot()'s one-way "let the hardware watchdog do it instead" signal" — When the reset timer cannot
  arm, the supervisor stops feeding the WDT · related: XCUT.T13 · [H05]
- **CORE.N170** RISK · `tests/test_system_service.py:428-429` — "each retry logged its own failure -
  bounded by print_log.py's own history/count caps" — A persistently raising NTP callback logs via err_s
  (errno=1, `src/system_service.py:138`) on every uptime tick until the 120 s fallback: 120 persisted
  entries per boot · [H05]
- **CORE.N171** SETTLED · `tests/test_system_service.py:450-452` — "the value must stay perfectly stable
  for the rest of this boot once resolved - never re-picked, never "upgraded" from random to NTP" — Boot
  signature resolves once per boot; outside observers detect reboots by change · related: CORE.S01 ·
  [H05]
- **CORE.N172** SETTLED · `tests/test_system_service.py:849-851` — "owner-confirmed design: unlike
  reboot_system()'s reset_timer guard, this degrades gracefully rather than forcing a reboot" —
  Uptime-timer arm failure → no uptime, no reboot, logged via non-persisting pr.err() (no FRAM evidence)
  · [H05]
- **CORE.N173** ASSUME · `tests/test_system_service.py:1168-1173` — "Regression test for the real
  "wrnno=10" bench-hardware bug: _log_dead_task()'s CancelledError branch used to log via the
  non-persisting self.pr.err()" — Single dated bench finding; CancelledError deaths now persist errno=6
  · [H05]
- **CORE.N174** LIMIT · `tests/test_system_service.py:1291-1293` — "The one branch in setup() no other
  test reaches: get_int_values() answering None" — Corrupt system-settings store keeps the constructed
  debug level · [H05]
- **CORE.N175** ASSUME · `tests/test_system_service.py:1370-1371` — "WP8: every other
  caller-supplied-callback call site in this codebase already persists via err_s()" — Codebase-wide
  consistency claim made from a retired work-package pass · [H05]

## tests/test_ticks_rollover.py

- **CORE.N176** ASSUME · `tests/test_ticks_rollover.py:2` — "Every real src/ ticks_ms()/ticks_diff() use
  site shares the same bounded-short-timeout shape" — The test enforces only "no raw subtraction"; the
  bounded-short claim is not checked, and stored-ticks sites contradict it · covered-by: DOC.S23 · [H05]

## digital_twin/README.md

- **CORE.N177** INVAR · `digital_twin/README.md:503-507` — "a reset arriving before the loggers finish
  `setup()` is dropped by design and the restore then puts the old history straight back" — ResetErrors
  before setup completes is silently dropped (by design); test must poll first · [H06]

## tests/test_digital_twin_sensortask_integration.py

- **CORE.N178** LIMIT · `tests/test_digital_twin_sensortask_integration.py:789-790` — "the command's
  duration is a hardcoded 300s no client can shorten, so the unpause half is driven through the same
  SystemService call" — Auto-unpause after `mempause` is not exercised end to end · [H06]

## tests_hardware/README.md

- **CORE.N179** ASSUME · `tests_hardware/README.md:1224-1227` — "`_TASK_FAIL_MAX` (300) would otherwise
  trip a real reboot around the 4th cycle (~7s)" — Supervisor-restart test deliberately stops at ~3.6 s;
  constants copied from `src/system_service.py:44-46`. · related: XCUT.T02 · [H08]
- **CORE.N180** TODO · `tests_hardware/README.md:1280-1286` — "`_reboot()`'s own alarm-pool-exhaustion
  fallback (`_force_watchdog_starve = True`) is mock-only." — Deferred to a dedicated session (queue
  G3). · related: XCUT.T13 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **CORE.N181** TODO · `REAL_HARDWARE_TEST_QUEUE.md:245` — "Owner, 2026-09-24: run it once more in the
  next bench sitting for extra evidence; a third pass closes it" — R5 OPEN: WP5 deferred-config-write
  re-confirmation (two green runs so far). · [H08]
  ⟨4dc80ef: R5 closed 2026-09-25 (third BMP3XX pass), row and BACKLOG entry retired (6e40e27)⟩
- **CORE.N182** TODO · `REAL_HARDWARE_TEST_QUEUE.md:273` — "`_reboot()`'s alarm-pool-exhaustion fallback
  (`_force_watchdog_starve = True`) is mock-only." — G3 OPEN. · related: XCUT.T13 · [H08]
  ⟨4dc80ef: G3 done 2026-09-25: reboot_fallback_starves_the_watchdog.py + test_watchdog_starvation.py,
  3/3 (79423dd)⟩

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **CORE.N183** LIMIT · `HARDWARE_TEST_HANDOVER.md:40` — "no silicon trigger for a write failure exists;
  it must simply stay quiet" — `config_manager.py`'s unpersisted-config path (`E4`/`E14`) untestable on
  silicon. · related: CORE.T02 · [H08]
  ⟨4dc80ef: section retired with the file (03f8bcf): open rows moved to BACKLOG.md "Real-hardware work
  still owed"; the traps live in tests_hardware/README.md, CLAUDE.md and SPECIFICATION.md⟩

## pyproject.toml

- **CORE.N184** SUPPRESS · `pyproject.toml:230-232` — "api_response.py calls a reader's `_set_dict_cfg`
  across objects by design" — src/api_response.py: SLF001. · [H09]
- **CORE.N185** SUPPRESS · `pyproject.toml:253-263` — "ANN401, category 1 - heterogeneous **kwargs ...
  PEP 692's Unpack[TypedDict] is the real fix and unavailable" — src/print_log.py and four tests files:
  ANN401; removal trigger: stubs declare TypedDict properly. · related: PLAT.T05 · [H09]

## tests_scripts/test_device_script_config_flush.py

- **CORE.N186** MIRROR · `tests_scripts/test_device_script_config_flush.py:130-137` — "The `.cfgmgr` hop
  above is only correct while _set_mgr_cfg persists through that attribute." — Guard pins
  `src/base_classes.py::_set_mgr_cfg` writing through `self.cfgmgr` · [H10]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **CORE.N187** MIRROR · `tests_scripts/test_digital_twin_ci_suite_errcount.py:24-26,44-46` —
  "\"counter\" bumps on errors AND warnings alike" / "print_log.py pre-fills the history deque with its
  own \"nothing recorded\" sentinel, published as type \"N\"" — Host parser encodes src/print_log.py's
  publication semantics (shared counter, ten-slot ring, "N" sentinel) · related: CORE.T05 · [H10]

## tests_scripts/test_persistence_write_marker_completeness.py

- **CORE.N188** ASSUME · `tests_scripts/test_persistence_write_marker_completeness.py:24-29` —
  "config_manager.py's write_config() short-circuits on `if not changed` BEFORE staging anything" — Two
  exempt tests rest on this src behaviour; one on `_VAL_NH`'s exact 3..1024 bound ("at exactly 1024 it
  would be valid and this would be a real flash write") · related: CORE.T02 · [H10]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **CORE.N189** INVAR · `SPECIFICATION.md:159-161` — "`import async_manager` silently resolves to
  whichever file defines that name — always import by name from `config_manager`/`base_classes`, never
  `async_manager`" — Import-hygiene rule for the flat frozen namespace; no lint/test guard found (grep
  of scripts/tests/src/buildgen). · [H12]
- **CORE.N190** RISK · `SPECIFICATION.md:161-163` — "a read can't detect on-disk corruption after that,
  and `write_config()` silently repairs an externally-corrupted file from the cache (accepted: this
  device is the file's only writer)" — Accepted: in-RAM cache wins over disk; premise "only writer"
  (mpremote/manual edits, tests) is an assumption. · related: CORE.T01 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **CORE.N191** ASSUME · `SPECIFICATION.md:557-559` — "calling `set_level()` at any time is safe — no
  interrupt handler touches logging, `self.level` is a single atomic-store `int`" — Safety rests on no
  IRQ/timer callback ever logging; nothing enforces it. · related: XCUT.T08 · [H12]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **CORE.N192** RISK · `SPECIFICATION.md:615-617` — "int→float has a known, accepted gap (every int
  representable as float only up to the mantissa precision, F.1) — accepted since no registered float
  field's bounds go near it (largest today: BMP3xx's `SeaLevelOffs` at `5000.0`)" — Accepted precision
  gap premised on current bounds. · related: CORE.T03 · [H12]

## SPECIFICATION.md Part C intro, C.1-C.2 (1475-1535)

- **CORE.N193** INVAR · `SPECIFICATION.md:1504-1505` — "Name-mangled (`__`) methods are reserved for
  when mangling itself is load-bearing — `src/` has none." — Convention claim; no lint guard named.
  (low) · [H12]

## SPECIFICATION.md Part C.5 / C.5.1-C.5.3 (Config schema system, 1699-1797)

- **CORE.N194** SETTLED · `SPECIFICATION.md:1717-1720` — "`ConfigManager` carries three defensive
  type-mismatch catches ... as pure defense-in-depth ... don't remove them" — Kept catches; premise
  "REST validation already guarantees clean input". · [H12]
- **CORE.N195** RISK · `SPECIFICATION.md:1722-1725` — "constructing a `ConfigManager` with a schema
  narrower than the full production one is dangerous — `setup()` ... silently drops it on rewrite" —
  Operational hazard for scripts/tests; caller discipline only. · related: HW.T03 · [H12]
- **CORE.N196** SETTLED · `SPECIFICATION.md:1733-1735` — "a plain sync `get_cfg_schema()` (no I/O,
  deliberately not `async`) ... `NeopixelDriver` is the one class with no schema" — Deliberate API
  shape. · [H12]
- **CORE.N197** LIMIT · `SPECIFICATION.md:1745-1749` — "Since WP5 ... `\"persisted\"` here really means
  \"validated and staged\" - a genuine disk write failure surfaces only later, as a logged `errno` on
  `cfgmgr.pr` ... none is expected to" — Client sees success before the flash write; settled. · related:
  CORE.T02 · [H12]
- **CORE.N198** INVAR · `SPECIFICATION.md:1749-1752` — "A push callback always receives the coerced,
  persisted value, not the caller's raw one" — Setter contract. · related: CORE.T04 · [H12]
- **CORE.N199** INVAR · `SPECIFICATION.md:1753-1756` — "For an `int`-typed field, narrow with
  `type(value) is not int`, not `isinstance` ... Every setter's return contract is uniformly `bool`" —
  bool-is-int convention; no guard named. · related: CORE.S12 · [H12]
- **CORE.N200** INVAR · `SPECIFICATION.md:1765-1767` — "`get_dict_cfg()` must keep its own narrower
  explicit field list (excluding the special-alone field), since `ConfigManager.get_dict()` is
  all-or-nothing and would `KeyError`" — Command-only field constraint. · [H12]
- **CORE.N201** LIMIT · `SPECIFICATION.md:1777-1781` — "deliberately not through `_push_callbacks` ...
  The caller-visible status stays `\"Failed\"` regardless of correction success — the repair is silent."
  — Recovery chain design; concurrency hazard seeded. · related: CORE.S05 · [H12]

## SPECIFICATION.md Part C.6 (Data model, 1799-1805)

- **CORE.N202** ASSUME · `SPECIFICATION.md:1808-1809` — "Every current namedtuple is flat scalars only —
  check this first if a new driver adds a list/nested-tuple field" — Guard by review only. · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **CORE.N203** SETTLED · `SPECIFICATION.md:1821-1832` — "`reset()` writes unconditionally;
  `_store_err()` does not. The asymmetry is deliberate." — Fix for partial ResetErrors in the boot
  window (2026-09-11). · related: CORE.S04 · [H12]
- **CORE.N204** INVAR · `SPECIFICATION.md:1866-1869` — "`pr.err_s`/`pr.wrn_s` (async, persist to
  history/FRAM) for anything counting against `get_error_counter()`; `pr.err`/`pr.wrn` (sync,
  non-persisting)" — Log-tier contract (UART repeats via sync `pr.err` disputed). · related: UART.S01 ·
  [H12]
- **CORE.N205** INVAR · `SPECIFICATION.md:1892-1895` — "a teardown/cleanup method on a class with no
  logger of its own must return `bool`, not `None`" — Silent-failure-masking convention
  (`AsyUDPSocket.disconnect()`, `WebserverService._close_writer()`, `UART.deinit()`). · [H12]

## SPECIFICATION.md Part C.7.1 (Running errno/wrnno table, 1893-1941)

- **CORE.N206** ASSUME · `SPECIFICATION.md:1940` — "`api_response.py`'s `handle_set_cmd()` — 99 | — |
  ... fixed at 99 since it runs against any registered module's `.pr`" | errno 99 lands in the calling
  module's history; collision with FRAM's own 99 or a future module's 99 not checked. (low) · related:
  CORE.S06 · [H12]

## SPECIFICATION.md Part C.7.3 (A failed config write costs persistence, 1975-2000)

- **CORE.N207** INVAR · `SPECIFICATION.md:1991-1996` — "No write is ever retried ... exactly two write
  sites and nothing that re-runs either on its own (no timer, sleep or loop — pinned structurally by
  `tests/test_config_manager.py`)" — Enforced structurally by test. · related: CORE.T02 · [H12]
- **CORE.N208** SETTLED · `SPECIFICATION.md:2001-2006` — "Bounded by boots, and deliberately no further
  - settled (owner, 2026-09-25). ... Don't add a cross-boot skip" — Do-not-reopen; one flash write
  attempt per boot while repair needed. · related: CORE.T12 · [H12]

## SPECIFICATION.md Part C.10 (Typing conventions, 2300-2308)

- **CORE.N209** INVAR · `SPECIFICATION.md:2310-2311` — "`TYPE_CHECKING` guarded via `try/except ImportError: TYPE_CHECKING = False`,
  never unconditional. PEP 604 `X — None` everywhere" | Typing conventions (UP007 enforces the `Union`
  half; the guard shape is also what `_strip_type_checking.py` matches). · related: GEN.S12 · [H12]

## SPECIFICATION.md Part C.13 (Readiness-gate scheme, 2363-2378)

- **CORE.N210** INVAR · `SPECIFICATION.md:2376-2380` — "Gate name/polarity is standardized:
  `self.initialized: bool = False → True` — except ... `ConfigManager.valid`" — Naming convention with
  one exception. · covered-by: XCUT.T12 · [H12]

## SPECIFICATION.md Part C.14 / C.14.1 (Instance naming, 2380-2428)

- **CORE.N211** ASSUME · `SPECIFICATION.md:2428-2430` — "The default (empty extension) case reproduces
  every existing path/filename/dict-key byte-for-byte" — Claimed and tested by
  `tests/test_config_manager.py` + per-driver regression tests. · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **CORE.N212** SETTLED · `SPECIFICATION.md:2653-2656` — "Quoting annotations (owner decision,
  2026-09-24) ... existing files are not mass-edited to the rule" — Rule applies to new/touched lines
  only; mixed style accepted. · [H12]
- **CORE.N213** INVAR · `SPECIFICATION.md:2730-2732` — "A pure reorder ... verified via an AST-level
  comparison, not just a visual diff" — No tool named for the AST comparison. · related: CORE.T09 ·
  [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **CORE.N214** LIMIT · `SPECIFICATION.md:3343-3345` — "`ErrNum` mixes errnos and wrnnos in one ring
  sharing a number space ... Filter on `ErrType == \"E\"`." — Log-reading trap from shared number
  spaces. · related: XCUT.T07 · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **CORE.N215** SETTLED · `SPECIFICATION.md:3485-3487` — "`config_manager.py`'s `type(x) is not int`
  stays correct either way and is the form to copy; don't add the CPython-only guard" — Do-not-add rule
  for a bool guard (one was written and removed 2026-09-13). · [H13]
- **CORE.N216** RISK · `SPECIFICATION.md:3496-3497` — "accepted, since no real schema field's bounds go
  near it" — Accepted-by-assumption: holds only while no schema bound exceeds 2**24. · related: PLAT.T08
  · [H13]

## SPECIFICATION.md Part F.2 — Blocking calls / timeout-wrapping

- **CORE.N217** ASSUME · `SPECIFICATION.md:3616-3618` — "`start_and_check_tasks()`'s `task_errors`
  counter escalates repeated respawn failures to watchdog starvation" — Recovery claim for a wedged bus
  depends on this escalation path actually starving the WDT (not verified here). · related: XCUT.T02,
  XCUT.S01 · [H13]
- **CORE.N218** RISK · `SPECIFICATION.md:3633-3653` — "one narrow, accepted residual window (WP5,
  2026-09-16) ... a power loss landing in that same brief window loses the just-accepted config change
  silently" — Accepted residual risk of the deferred flush. · related: CORE.T02, XCUT.T10 · [H13]
- **CORE.N219** ASSUME · `SPECIFICATION.md:3644-3646` — "In practice this window is a single scheduler
  tick (microseconds to low milliseconds)" — Unmeasured estimate; the deferred flush task can queue
  behind other work. · related: CORE.T02 · [H13]
- **CORE.N220** INVAR · `SPECIFICATION.md:3634-3635` — "Every real flash write is still *triggered* only
  through the REST PUT path — nothing else ever calls `ConfigManager.write_config()`" — Convention-only
  invariant the watchdog/WiFi backstop safety relies on. · related: CORE.T02 · [H13]
- **CORE.N221** ASSUME · `SPECIFICATION.md:3650-3651` — "never corrupts anything: the next boot's
  `setup()` repairs whatever the interrupted write left, C.7.3" — littlefs/`setup()` repair claim under
  power loss. · related: XCUT.T10 · [H13]

## SPECIFICATION.md Part G.2 — Known reusable primitives

- **CORE.N222** INVAR · `SPECIFICATION.md:4171-4173` — "`type_or_range_error()`/`coerce_numeric()` ...
  Never hand-roll a cast/range comparison." — Convention-only validation primitive rule. · related:
  CORE.T03, XCUT.T15 · [H13]
- **CORE.N223** INVAR · `SPECIFICATION.md:4174-4176` — "validate payload, `try/await` the callback,
  `except Exception` → `err_s(...)` → `\"Failed\"`" — Callback dispatch-guard shape; broad catch by
  design. · related: XCUT.T11 · [H13] ⟨quote not matched at the anchor⟩
- **CORE.N224** INVAR · `SPECIFICATION.md:4179-4183` —
  "`Lockable`/`LockedCounter`/`LockedFlag`/`LockedValue`, never a bare module-level variable plus an ad
  hoc lock ... `make_logger()`/`PrintLog`... never a bespoke print-based counter" — Convention-only
  rules. · related: CORE.T08 · [H13] ⟨quote not matched at the anchor⟩
- **CORE.N225** INVAR · `SPECIFICATION.md:4184-4192` — "Anything returning a
  `get_log()`/`get_error_counter()` result annotates it `\"ErrorLog\"` — never a re-spelled `dict[...]`"
  — Typing convention; historical counts "12 `src/` files and 7 test files", "three" ignores removed. ·
  [H13]
- **CORE.N226** INVAR · `SPECIFICATION.md:4244-4252` — "`instance_name()`, never a hand-rolled
  string-concatenation ... `_WIRING` ... never a getter/callback function ... every top-level module
  implements `get_error_sources()`/`get_loggers()`" — Three convention-only shape rules (C.14.1-C.14.3).
  · related: XCUT.T15 · [H13]
- **CORE.N227** INVAR · `SPECIFICATION.md:4253-4259` — "Only ever called from a one-time or bounded-loop
  context, never a place that could keep feeding a genuinely hung system forever - that constraint lives
  with the caller" — `feed_watchdog()` caller-discipline rule; nothing mechanical. · related: XCUT.T03 ·
  [H13]

## SPECIFICATION.md Part H.6 — Errcount and dispatch-only conventions

- **CORE.N228** LIMIT · `SPECIFICATION.md:4517-4518` — "a fixed `history_length`-long list, no per-entry
  timestamp — `type` only colors `num`" — Error history carries no timing. · related: XCUT.T24 · [H13]

## SPECIFICATION.md Part I.2 — Hotspot catalog

- **CORE.N229** SETTLED · `SPECIFICATION.md:4894-4898` — "**Each FRAM-backed logger's
  `PrintLogHistoryStore.setup()` stays first in its module's own `setup()`** ... (2026-09-21)" — Owner
  decision; cites undefined "measures A and B". · related: CORE.T05, DOC.S16 · [H13]

## SPECIFICATION.md Part I.4 — Multi-stage memory-error scheme, (a)-(e)

- **CORE.N230** ASSUME · `SPECIFICATION.md:5008-5011` — "the `task_errors` counter escalates past
  repeated restarts to `reboot_system()`, at which point the loop stops feeding the watchdog" — Stage
  (d) claim; plan seeds show the supervisor's reboot branch `return`s and reboot timer behaviour. ·
  related: XCUT.T02, XCUT.S11, XCUT.S03 · [H13]

## CLAUDE.md

- **CORE.N231** ASSUME · `CLAUDE.md:199-201` — "every real flash write is reachable only through the
  REST PUT path, so a device whose API is unreachable structurally cannot have a write in flight" — Also
  the rationale for ignoring ruff ASYNC230 (pyproject.toml:73-74). Two exceptions:
  `ConfigManager.setup()` rewrites config files at boot (src/config_manager.py:433-465), and an accepted
  PUT's flush runs in a task after the response (:354). · related: CORE.S02, CORE.T12, CORE.S17 · [H14]

## README.md

- **CORE.N232** ASSUME · `README.md:562-573` — "pushes any accepted `DebugLevel` write straight out to
  every other already-constructed module's own `PrintLog.set_level()`, live ... (confirmed directly" —
  CFGMGR loggers never receive `debug`. · related: CORE.S08, XCUT.T08 · [H14]
- **CORE.N233** ASSUME · `README.md:563-565` — "saved to disk shortly after, off the request's own
  critical path (`config_manager.py`'s deferred-flush design, SPECIFICATION.md Part F.2)" — A failed
  deferred flush is invisible to the client that got "Valid". · related: CORE.T02, CORE.S17 · [H14]
- **CORE.N234** DRIFT · `README.md:611-613` — "a JSON integer where a `\"float\"` field is declared
  (e.g. `60` instead of `60.0`) is correctly rejected as `\"Invalid\"`, not a bug" — The code accepts
  it: `coerce_numeric()` blanket-accepts int → float (src/config_manager.py:130-134), used by
  `type_or_range_error()` (:163-164). · related: CORE.T03 · [H14]
- **CORE.N235** DRIFT · `README.md:635-636` — "(logged as `SYSTEM ... reboot triggered!` at `DebugLevel >= 4`)"
  — It is an `err_s` (src/system_service.py:251) and prints at level ≥ 1 (src/print_log.py:54, 205)
  (low). · [H14]

## BACKLOG.md

- **CORE.N236** TODO · `BACKLOG.md:21-35` — "fixed (WP5, 2026-09-16), pending real-hardware
  re-confirmation" — Unnumbered item "config-persisting PUT /sensors reset its own HTTP connection":
  fixed by deferring the flash write to a task; still owed one more BMP3XX-arm bench pass (queue R5,
  owner 2026-09-24), then closes; the ISL29125 arm is item 30. Status: open (silicon). · related:
  CORE.T02, HW.S21 · [H15]
  ⟨4dc80ef: R5 closed 2026-09-25, this BACKLOG entry retired (6e40e27); the residual window stays in
  SPECIFICATION.md:3638-3660⟩
- **CORE.N237** RISK · `BACKLOG.md:28-31` — "including the accepted residual risk window and its
  interaction with the WiFi-power-cycle backstop" — The deferred write still disables IRQs port-wide for
  the flash write (rp2_flash.c); an accepted residual risk window (SPEC F.2). · related: BUS.T12,
  PLAT.T12 · [H15]
  ⟨4dc80ef: BACKLOG entry retired with R5 (6e40e27); the residual window stays in
  SPECIFICATION.md:3638-3660⟩
- **CORE.N238** TODO · `BACKLOG.md:68-72` — "flagged by the owner as implementable more efficiently" —
  Unnumbered: task-supervisor error-budget counter to be re-implemented without changing observed
  behaviour. Status: open. · related: XCUT.T02, PAR.S04 · [H15]
- **CORE.N239** TODO · `BACKLOG.md:94` — "a real-hardware test for _reboot()'s alarm-pool-exhaustion
  fallback" — Follow-on (c). · related: XCUT.T13 · [H15]
- **CORE.N240** SETTLED · `BACKLOG.md:167-173` — "Decided by the project owner: no — a write is fast
  enough not to matter" — #4 `write_config()` needs no long-block coordination; `get_long_block_lock()`
  stays removed. · related: DOC.S13 · [H15]
- **CORE.N241** ASSUME · `BACKLOG.md:168-170` — "it never happens on its own/automatically anyway (only
  ever triggered by a real user interaction via the REST layer)" — Premise of #4; plan seeds say
  `ConfigManager.setup()` rewrites/repairs files at boot on its own, so the premise may be false. ·
  related: CORE.S02, CORE.T12 · [H15]
- **CORE.N242** OPENQ · `BACKLOG.md:510-512` — "Unchecked: whether a stored value outside a tightened
  bound is rejected on the next write or silently falls back to the default" — Read-path handling of an
  out-of-bound stored value untraced. · related: CORE.T01 · [H15]

## Commit messages (chronological)

- **CORE.N243** SETTLED · `commit 368fa83` — "task-supervisor error-budget asymmetry are both
  intentional (flagged for a more efficient, behavior-preserving implementation in the refactor)" —
  Error-budget counter efficiency rewrite deferred. · tracked: BACKLOG "Refactor targets"
  (task-supervisor error-budget counter) | - · [H17]
- **CORE.N244** OPENQ · `commit 9cd4a99` — "flags that task-respawn recovery is a basis to revisit (not
  assumed-complete) during the refactor" — Supervisor task-respawn as a recovery basis was to be
  revisited, never explicitly closed in a commit message. · status: partially covered by later
  supervisor work (Step 6 self-healing audit PR #36); no explicit closure found (low) | related: CORE.T*
  · [H17]
- **CORE.N245** OPENQ · `commit 6f12d22` — "an open question about whether swallowed exceptions in
  low-level forwarding methods are still logged" — Open question on silent swallowing in forwarding
  methods. · status: no later closure found by grep (low; likely resolved in the src/ promotions) |
  related: XCUT · [H17]
- **CORE.N246** SETTLED · `commit 9243049` — "Decided: keep all 3 exception-hardening catches from the
  earlier audit, revisit once the real REST layer exists." — Revisit of config_manager's wrong-type
  hardening deferred until the REST layer exists. · status: done — "config_manager's defensive catches"
  pruned as resolved in 5b70e4b (SPECIFICATION records them as intentionally dead) | - · [H17]
- **CORE.N247** RISK · `commit 83c08ae` — "reads no longer detect the config file being
  deleted/corrupted out-of-band after a valid init ... a write silently repairs an externally-corrupted
  file" — Deliberate in-memory cache consequence. · tracked: SPECIFICATION.md:162 | - · [H17]
- **CORE.N248** TODO · `commit 25cb925 (and 2a3ea41)` — "sensortask-wozi.py's last_task_err's -1
  sentinel is deliberately deferred to the future sensortask-*.py functional refactor" — Deferred
  sentinel migration. · status: done (no `last_task_err` left in src/, buildgen/ or SPECIFICATION —
  grep) | - · [H17]
- **CORE.N249** INVAR · `commit c53fa5e` — "a driver's own async setup() must call self.pr.setup()
  itself for FRAM persistence to activate" — Caller discipline for FRAM-backed logging activation. ·
  tracked: src/base_classes.py:5 | - · [H17]
- **CORE.N250** SETTLED · `commit f3924e1 (reverts af24a01's timeout)` — "start_timers() is back to its
  plain, unbounded await self.timers_running.wait()" — Owner rejected a software timeout racing the WDT
  for both start_timers() and the one-shot reboot timer ("brittle wrt. wdt timeout settings"); a dropped
  soft-Timer callback stays a watchdog-backstop case. · tracked: SPECIFICATION.md:2209, 3454-3455 |
  related: CORE.T*, PLAT.T* · [H17]
- **CORE.N251** TODO · `commit c152d8b / 0a0727c / e360f34 / 6780011` — "The REST config-write path for
  BackupPeriod/BackupMaxAge/WaitTimeNTP remains a known, documented gap ... deliberately deferred to a
  single consolidated pass" — Generic config setters deferred to a consolidated pass. · status: done
  (generalized setter dispatch, PR #26 / SPECIFICATION Part G) | - · [H17]
- **CORE.N252** TODO · `commit eff19bf` — "note the project owner's stated future direction (predefined
  common error classes, per-driver reporting) as deferred work in BACKLOG.md" — Owner-stated future
  direction for common error classes. · status: done — closed in BACKLOG as "scheme designed and
  applied" (common errno slots 10/11/12, SPECIFICATION Part C.7 "Common error classes"), pruned in
  5b70e4b | related: CORE.T* · [H17]
- **CORE.N253** TODO · `commit 7bd9748` — "Added a tracked BACKLOG.md entry for renaming the
  misleadingly I2C-named parameter project-wide, deferred" — max_i2c_err rename. · status: done (0
  occurrences of `max_i2c_err` in src/) | - · [H17]
- **CORE.N254** LIMIT · `commit 3383dee` — "config_manager.py's make_dict() repr()-parsing quirk with
  list/nested-tuple fields - dormant today ... a real landmine for the next config field added" —
  Restored landmine. · status: SPECIFICATION C.6 describes make_dict; whether the repr-parsing landmine
  note survives was not confirmed (low) | related: CORE.T* · [H17]
- **CORE.N255** SETTLED · `commit a2ef9ec` — "The caller-visible status stays \"Failed\" regardless -
  only the persisted value is silently repaired" — Failed-push recovery chain silently rewrites
  persisted config. · tracked: SPECIFICATION Part C.5.2.2 (per commit) | related: CORE.T* · [H17]
- **CORE.N256** SETTLED · `commit a015e66 / 59d6b7b` — "widen every Timer.init() except-OSError site to
  catch (OSError, MemoryError) defensively ... Timer.init()'s only own failure mode is
  OSError(MP_ENOMEM) - no separate MemoryError path exists" — Defensive MemoryError arm kept although
  source says unreachable (1.28 source); tests use a fake raise_on_arm_exc to reach it. · tracked:
  SPECIFICATION Part C.9 (per commit) | related: PLAT.T* · [H17]
- **CORE.N257** SETTLED · `commit acc4993` — "print_log.py get_log() dead _NO_WRN branch (kept for
  symmetry with the reachable _NO_ERR arm and for a well-defined FRAM-init value)" — Intentional dead
  branch. · tracked: SPECIFICATION Part E.5.1 (per commit) | - · [H17]
- **CORE.N258** RISK · `commit 72d658b` — "the worst case from a level change racing a log call is one
  line using the old-vs-new threshold - a transient, explicitly accepted non-issue" — Debug-level
  registry race accepted; relies on "the one IRQ handler in src/ never touches logging". · tracked:
  WIRING_CONTRACT.md then (deleted); current home not verified (low) | related: CORE.T* · [H17]
- **CORE.N259** SETTLED · `commit 72d658b (reverts ec2e803's SharedLevel)` — "Reverted entirely:
  base_classes.py's SharedLevel is gone ... Reimplemented with a registry of function references" —
  Owner rejected a shared mutable level; registry design is settled. · tracked: SPECIFICATION
  (set_level_setters) per later docs | - · [H17]
- **CORE.N260** LIMIT · `commit 3986be9` — "coerce_numeric()'s int->float direction is a blanket accept
  with no exact-round-trip check, so it silently loses precision beyond a float's mantissa (2**24 on
  RP2040 ...)" — Accepted numeric-coercion precision gap; Unix port (double) cannot reproduce rp2
  (single) behaviour. · tracked: SPECIFICATION.md:616, 3494-3495 | related: PLAT.T* · [H17]
- **CORE.N261** NOTE(REVERT) · `commit 9fe6d15 (reverts 84a40f4's TaskCheckSecs + heap snapshot)` — "the
  finding turned out to be a stale, never-cleared FRAM history entry rather than a live, reproducing
  issue" — Debug tier removed; standing rule that FRAM history survives reflash. · tracked:
  SPECIFICATION Part C.7, CLAUDE.md FRAM-evidence rule | - · [H17]
- **CORE.N262** INVAR · `commit 6f430c7` — "constructing it with fewer fields than a config file
  actually holds silently drops the other real fields on rewrite" — ConfigManager narrow-schema hazard.
  · tracked: SPECIFICATION.md:1724 (Part C.5) | related: CORE.T* · [H17]
- **CORE.N263** WORKAROUND · `commit 8428517` — "system_service's storage_pause moved to a TYPE_CHECKING
  _StoragePause Protocol, since Callable[[bool], None] cannot express a keyword-only parameter" — Typing
  workaround for keyword-only callback. · status: by design (low) | - · [H17]
- **CORE.N264** INVAR · `commit 8d77994` — "Records in BACKLOG.md the seven src/ modules that number
  inside the reserved range today - no live clash, a real defect the moment any of them gains a logger
  reach-through" — errno reserved-range overlap. · status: done-in 58abf8f ("close items 15 and 22";
  still open/deferred at b0f755c) | - · [H17]
- **CORE.N265** NOTE(OWNER) · `commit 793eb99 / 54359b9 / 9ac59cf` — WP6 boot-time watchdog feeding; WP7
  timer stagger design intent; Topic 11 err() -> err_s() upgrade, errno/wrnno realignment, "every module
  shall have optional FRAM logging ... FRAM module itself is the sole exception"; WP5 fire-and-forget
  create_task for PUT-backed routes; WP8 5 genuine print-only gaps — Decisions from the WP restart. ·
  status: to verify in later chunks (WP1-WP8 landed 2026-09-16..18) | - · [H17]
- **CORE.N266** NOTE(DESIGN) · `commit 5da0783` — "wrn_s()/err_s() take repeat=True, which still counts
  the occurrence ... but spends no history slot" — Item 35 closure mechanism. · tracked: SPEC C.7 (not
  re-verified) | - · [H17]
- **CORE.N267** NOTE(DEFERRED-RULE) · `commit 58abf8f` — "The seven modules numbering inside the
  reserved errno/wrnno range renumber on their next substantial change (C.7.1)" — Reserved-range
  violation left in place until next change. · tracked: SPEC C.7.1 | related: CORE.T* · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **CORE.N268** INVAR · `https://github.com/hundertvolt/sensors/pull/40#issuecomment-5344576386` — "the
  three top-level `await self.cfgmgr.get_*_values()` calls in `monitor_loop()` execute as one
  uninterrupted synchronous unit" — No-lock justification rests on `_get_values()` never suspending on
  the success path; only the error path awaits `pr.err_s`. Still holds at 2a88cc8
  (src/asy_notification_service.py:343-345, src/config_manager.py:240-293); recorded only in the PR
  comment · UNTRACKED | - · [H17]

## Delta `2a88cc8` → `4dc80ef` (main head, V11)

- **CORE.N269** TODO · `BACKLOG.md:21-35` — "Four modules this branch changed substantially still number
  inside the reserved range" — asy_ntp_client, asy_wifi_service, asy_notification_service and
  config_manager were changed without C.7.1's renumbering; the reserved-range rule is recorded but
  unapplied. · covered-by: XCUT.T07 · [D1]
