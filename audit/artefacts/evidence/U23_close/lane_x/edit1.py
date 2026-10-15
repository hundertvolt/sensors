"""Lane X edits, part 1: A.8, B.14.4, L.5, G.2 (exact replacements, each found exactly once)."""
import sys
from pathlib import Path

SPEC = Path(sys.argv[1])
text = SPEC.read_text(encoding="utf-8")
EDITS = []


def edit(old: str, new: str) -> None:
    EDITS.append((old, new))


# X7, X41, X44: A.8 opening.
edit(
    """and the envelope code catalog (L.4). It holds `device`, `envelopeCodes`, `resultWords` and `routes`
in `ROUTES` order, each route with its fields' facts: a GET lists every field except the
dispatch-only ones and those with a `defaultValue`, a PUT every field except the readonly ones, and
`GET /status` every errcount module. `tests_scripts/test_api_reference.py` pins it; this section is
its prose summary. The build refuses a settings key two groups would serve on one route, and a
logger name two modules would claim in `errcount` (L.6.6).""",
    """and the envelope code catalog (L.4). It holds `device`, `envelopeCodes`, `resultWords`,
`unavailableMarker` (`{"error": "unavailable"}`, its word `asy_base_classes.py`'s `UNAVAILABLE`),
`unknownCodeText` (`asy_api_response.py`'s `_UNKNOWN_DESCR`, "Unknown error"; both read from `src/`
by AST) and `routes` in `ROUTES` order, each route with its fields' facts: a GET lists every field
except the dispatch-only ones and an always-executed toggle (`ContMeas`, the one command a GET
cannot report), a PUT every field except the readonly ones, and `GET /status` every errcount
module. A field's facts are its API keys (`key`, `kind`, `unit`, `min`/`max`,
`minLength`/`maxLength`, `byteLength`, `shape`, `float`, `specialValues`, `path`, `format`, `codes`,
`mask`, `dispatch`, `alwaysExecuted`, `resolution`, `ignoredWhenSet`, `statusPath`; an enum's
options reduced to their values, a composite's sub-fields to their facts); the page-only hints
(`label`, `description`, `onLabel`, `offLabel`, `decimals`, `clearable`, `codeTones`, `confirm`)
stay out, and a definitions key in neither set fails the build (`api.field-key-unclassified`).
`tests_scripts/test_api_reference.py` pins it; this section is its prose summary. The build refuses
a settings key two groups would serve on one route, and a logger name two modules would claim in
`errcount` (L.6.6).""",
)

# X46: A.8 GET shapes, the /status sensors entry.
edit(
    """  `ConfigManager` — `CFGMGR_<name>`); `sensors` keys are `<source>_<field>`, one source per SGP40
  under its instance name (`SGP40`, `SGP40_<ext>`, Part C.14) and `UARTLINK` for dev's initiator.""",
    """  `ConfigManager` — `CFGMGR_<name>`); `sensors` holds one object per source with that source's
  fields — one per SGP40 under its instance name (`SGP40`, `SGP40_<ext>`, Part C.14:
  `BackupTS`/`RestoreTS`) and `UARTLINK` for dev's initiator (`Transfers`/`Failures`); the page reads
  each such field by its `path` (`[source, field]`), while its definitions key stays
  `<source>_<field>`.""",
)

# X45: A.8 /status fields, UnixTime after UTCTime.
edit(
    """  a module leaves the list at its next successful write (C.7.3). `UTCTime` — `null` until the
  first NTP sync, like `LocalTime`, and again while `NTPSynced` is false. `networking`'s link""",
    """  a module leaves the list at its next successful write (C.7.3). `UTCTime` — `null` until the
  first NTP sync, like `LocalTime`, and again while `NTPSynced` is false. `UnixTime` — the device's
  Unix seconds (an int) when the poll was answered, `null` until the first NTP sync; every age on
  the website is computed against it. `networking`'s link""",
)
edit(
    """  `SGP40_BackupTS`/`SGP40_RestoreTS` — `null` = none since boot,
  `0` = no timestamp (owner, 2026-09-29).""",
    """  `BackupTS`/`RestoreTS` under each SGP40 source — `null` = none since boot,
  `0` = no timestamp (owner, 2026-09-29).""",
)

# X42: A.8 PUT /status.
edit(
    """  300 s lives in the command callback. `/status` — `{"ResetErrors": true}` only: every registered
  error source resets concurrently, `HTTPDropped`'s window included, and `result.ResetErrors` answers
  `"Valid"`, or `"Failed"` when a store's write failed; any other value, and every other key, answers
  `"Invalid"`; a body without the key resets nothing. `/notification` — settings + `LightCmdLED`""",
    """  300 s lives in the command callback. `/status` — `{"ResetErrors": true}` only: every registered
  error source and the webserver's own log reset concurrently, `HTTPDropped`'s window included, and
  all are awaited before the answer; `result.ResetErrors` answers `"Failed"` when any reset raised
  or returned false, else `"Valid"`, and each raise is persisted once, after the resets, in the
  webserver's own history (errno 14, `CALLBACK`: `"Error log reset failed: <name> <exception>"`);
  any other value, and every other key, answers `"Invalid"`; a body without the key resets nothing.
  `/notification` — settings + `LightCmdLED`""",
)

# X29: A.8 controlled shutdown, the website's confirmation.
edit(
    """when no FRAM chip is set up, or the chip is lost or write-protected. The API takes one command per
request and asks no confirmation (owner, 2026-09-30).
""",
    """when no FRAM chip is set up, or the chip is lost or write-protected. The API takes one command per
request and asks no confirmation (owner, 2026-09-30). The website asks the browser's confirmation
before it sends a system command (`"<option label>?"`, e.g. "Reboot?", "Erase FRAM?"), the error reset
("Reset All Errors?") or the DNS fallback's Clear ("Clear Fallback DNS Servers?"), and a declined one
sends nothing (owner, 2026-10-01, asked about "A confirmation before clearing the DNS fallback list":
'Fine, and add a dialog to all system commands and the clear error history as well. But only on the
website, not on the API side. The API stays single command.').
""",
)

# X3: B.14.4 Cost, the window statistic.
edit(
    """timeout fires — its duration bounded by that timeout, its per-round cost by the host build's
spin-round test (`l1.lwip_host_spin_round_max_us`, `l1.lwip_host_spin_round_alloc_max_b`; 8.5 ms
and 32 B at worst on the host) and on the dev bench""",
    """timeout fires — its duration bounded by that timeout, its per-round cost by the host build's
spin-round test (`l1.lwip_host_spin_round_max_us` on the fastest round of every three consecutive
rounds, `l1.lwip_host_spin_window_rounds` (owner, 2026-10-13), and
`l1.lwip_host_spin_round_alloc_max_b` on every round; 8.5 ms for a single round and 32 B at worst on
the host) and on the dev bench""",
)

# X6: L.5 tag-value rule.
edit(
    """`@limits` bounds and choices, `@requires` values and `@web defaultValue`
  (`tag.non-finite-number`)""",
    """`@limits` bounds and choices, `@requires` values and `@web resolution`
  (`tag.non-finite-number`)""",
)

# X5: L.5 rule-id list, the @web group.
edit(
    """  `web.hidden-no-reason`, `web.hidden-not-alone`, `web.instance-group-missing`,
  `web.key-needs-readonly`, `web.key-needs-string`, `web.kind-unknown`, `web.kind-unresolved`,
  `web.maintenance-tag-missing`,""",
    """  `web.hidden-no-reason`, `web.hidden-not-alone`, `web.ignored-when-set-unknown`,
  `web.instance-group-missing`, `web.key-needs-number`, `web.key-needs-readonly`,
  `web.key-needs-string`, `web.kind-unknown`, `web.kind-unresolved`, `web.maintenance-tag-missing`,""",
)

# X43: L.5 rule-id list, the API-reference group.
edit(
    """  `api.source-unreadable`; the toolchain tables: `toolchain.lwip-table`,
  `toolchain.overrides-unloadable`; the twin wiring plan: `twin.no-address-rule`; the CLI:
  `cli.out-dir-unwritable`.""",
    """  `api.source-unreadable`, `api.wire-text-not-string`; the toolchain tables:
  `toolchain.lwip-table`, `toolchain.overrides-unloadable`; the twin wiring plan:
  `twin.no-address-rule`; the CLI: `cli.out-dir-unwritable`.""",
)

# X8: G.2 cross-language mirror catalog.
edit(
    """  simulates**; a `src/`-side policy change and its `js/` mirror are one change, not two. The
  mirrored pairs, each with its check: `js/mock-server.js` against the real `src/` endpoints, field
  for field, bound for bound; the website's copies of generator bounds (`js/definitions.js`'s
  `SUPPORTED_SCHEMA_MAJOR` and `MAX_DECIMALS`, and the shape rules of `validateDefinitions()`)
  against `buildgen/`, pinned by `tests_scripts/test_definitions_js_mirrors.py` and the shape corpus
  `tests_scripts/definitions_shape_cases.json`, which the Python shape check and the JS validator
  both read; and the facts `buildgen/` restates from `src/` with the two owner-kept catalogs (K.3),
  pinned to their sources both ways by `tests_scripts/test_buildgen_source_agreement.py`.""",
    """  simulates**; a `src/`-side policy change and its `js/` mirror are one change, not two. The
  mirrored pairs, each with its check: `js/mock-server.js` against the real `src/` endpoints, field
  for field, bound for bound (H.4); `js/api-contract.js`'s wire facts against `src/` — the four
  result words (`asy_config_manager.py`), `ERR_COUNT_CAP` (`asy_print_log.py`'s `_MAX_CNT`, the
  error counter's cap), `GMTIME_KEYS` (the first six keys of the generated
  `_gmtimestruct_to_dict()`) and `isUnavailable()` (the marker built from `asy_base_classes.py`'s
  `UNAVAILABLE`); the mock's own copies — `COUNTER_CAP`, `STANDARD_CODES`, `makeResponse()`'s
  unknown-code text (`_UNKNOWN_DESCR`), `LED_BUSY_DESCR`, `LED_DURATION_MEMBER`, `DNS_LABEL_MAX` and
  `DNS_FALLBACK_MAX` — against theirs; every device's dispatch-field definitions against the
  webserver's `_SYSTEM_CMDS`, `_PAUSE_TIME_FIELD` and `_LIGHT_CMD_FIELDS`; and a scan that `src/`
  spells the degraded-source marker only through `UNAVAILABLE` — all read as source and pinned by
  `tests_scripts/test_js_api_mirrors.py`, each pin biting on a planted mismatch. Each device's
  generated REST reference agrees with its definitions' routes, the result words and the mock's
  code table (`tests_js/api-reference-agreement.test.js`). The website's copies of generator bounds
  (`js/definitions.js`'s `SUPPORTED_SCHEMA_MAJOR` and `MAX_DECIMALS`, and the shape rules of
  `validateDefinitions()`) against `buildgen/`, and its `MAX_POLL_INTERVAL_MS` (2**31 − 1,
  `setTimeout()`'s ceiling) against the Python shape check's `_MAX_POLL_INTERVAL_MS`, pinned by
  `tests_scripts/test_definitions_js_mirrors.py` and the shape corpus
  `tests_scripts/definitions_shape_cases.json`, which the Python shape check and the JS validator
  both read; and the facts `buildgen/` restates from `src/` with the two owner-kept catalogs (K.3),
  pinned to their sources both ways by `tests_scripts/test_buildgen_source_agreement.py`. A JS test
  reads a JS module's own constant from its source rather than restating it
  (`tests_js/_source_constants.js`'s `readIntConst()`/`readObjectConst()`: `POLL_BACKOFF_MAX_MS`,
  `DEFAULT_TIMEOUT_MS`, the mock's `STANDARD_CODES`).""",
)

for old, new in EDITS:
    count = text.count(old)
    if count != 1:
        sys.exit(f"found {count} times:\n{old[:200]}")
    text = text.replace(old, new)
SPEC.write_text(text, encoding="utf-8")
print(f"applied {len(EDITS)} edits")
