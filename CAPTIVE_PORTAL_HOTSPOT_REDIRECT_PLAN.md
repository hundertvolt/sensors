# Captive-portal auto-popup: facts and implementation plan

**Status: temporary planning document.** Lifecycle: migrate any durable facts into
`SPECIFICATION.md` (Part A.5/A.8) and `tests_hardware/README.md`'s "Known assumptions and open
findings" list once implemented and verified, then delete this file — same pattern as
`WIFI_RECONNECT_INVESTIGATION.md`. Do not let this accumulate history once the work lands; it
exists to hand off a fully-scoped unit of work, not to become a permanent doc.

**Origin**: a conversational research thread (this repo's chat history, not a GitHub issue) about
why phones don't automatically pop up "Sign in to network" when joining the device's hotspot/AP
fallback, despite the DNS spoofer (`src/captive_dns.py`) already redirecting every domain to the
device's own IP. Two research passes (one external-sources-only, one including a project-wide code
read) converged on a single, small, well-corroborated fix. This document is that fix's complete
scope, written so a separate implementation session does not have to re-derive any of it.

---

## 1. Facts

### 1.1 The root cause (confirmed against this repo's own code)

`src/asy_webserver_service.py`'s `_serve_static()` (called from both `_get_static_index` for `/`
and `_get_static` for `/<path:filename>`) does `send_file(...)` for a real frozen-filesystem file,
and `abort(404)` for anything else (lines ~510-522). Every OS captive-portal probe
(`generate_204`, `hotspot-detect.html`, `connecttest.txt`, ...) hits a path that isn't a real
frozen file, so **every one of them currently gets a plain 404** instead of a signal that reads as
"portal present." DNS spoofing (`src/captive_dns.py`) is already correct and needs no change — it
already returns the AP's own IP for literally any queried domain, unconditionally.

### 1.2 What every working reference implementation does instead

Every reliable captive-portal implementation found in research answers *every* HTTP request while
the portal is active — never 404 — one of two ways: serve the portal page (200) for any path, or
302-redirect any unmatched path to the portal page. Sources (both research passes):

- [p-doyle/Micropython-DNSServer-Captive-Portal](https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal)
  — the literal upstream project `src/captive_dns.py`'s own header attributes as its DNS-side
  ancestor. Its paired web server doesn't route by path at all: it returns `index.html` for
  *any* request.
- [CDFER/Captive-Portal-ESP32](https://github.com/CDFER/Captive-Portal-ESP32) ("an ESP32 Captive
  Portal example that actually works") and
  [Nordesems/esp-captive-portal](https://github.com/Nordesems/esp-captive-portal): HTTP 302
  redirect (with meta-refresh/JS fallback for older clients) for any unmatched path, connection
  closed immediately after to avoid socket exhaustion on a constrained device.
- [foxblock/esp-captive-portal](https://github.com/foxblock/esp-captive-portal): confirms the
  per-OS probe list (Android 4.4+/6.0+ `generate_204`→204; iOS "Success" HTML;
  Windows 8-/10+ NCSI text; Firefox canonical-file check) and that a genuine catch-all makes
  enumerating them unnecessary.
- MicroPython's own official discussions
  ([#12012](https://github.com/orgs/micropython/discussions/12012),
  [#9264](https://github.com/orgs/micropython/discussions/9264)) confirm there's no
  MicroPython-native captive-portal library beyond exactly this DNS-spoof + catch-all pattern, and
  that arbitrary third-party portals (eduroam, WPA-Enterprise) are a different, out-of-scope
  problem — irrelevant here since this device is the AP, not a client of someone else's portal.

**Conclusion carried into this plan**: the fix is a *generic* catch-all, not a table of per-OS
paths/hostnames. Both the DNS layer (already generic) and the proposed HTTP fallback (path-agnostic
by construction — see §3) are indifferent to which OS or domain triggered the request. See §1.4 for
why an even simpler variant (redirect, not serve-content) was chosen for this codebase specifically.

### 1.3 New findings from this pass (external)

- **DHCP Option 114 (RFC 8910)** is real and growing (`esp-idf` added it in 5.4), but explicitly
  **out of scope**: it requires custom-option injection at the DHCP-server (lwIP `dhcps`) level.
  MicroPython's rp2 port doesn't expose that from Python/`src/` code — reaching it would mean
  patching MicroPython's own C DHCP server, a different and much larger unit of work. Search
  results also note most OSes still run their own HTTP-probe verification even when Option 114 is
  present, so it's a nice-to-have acceleration, not a required mechanism. **Recommendation: do not
  implement in this unit of work; optionally note as a BACKLOG.md future-idea line, project owner's
  call.**
- **Samsung hardcodes its connectivity-check DNS resolver**, bypassing DNS spoofing entirely
  (corroborated independently by both research passes: general search results and
  `foxblock/esp-captive-portal`'s README). The only known workaround (squatting the AP's own IP on
  `8.8.8.8`) has real downsides and is not recommended here — **this is a known, accepted,
  unfixable-from-this-side limitation, not a bug to chase.**
- **Post-Big-Sur macOS / some iOS versions can suppress the popup even with a correct
  implementation** (`CDFER` README) — an OS-side behavior change, not something firmware can fix.
  A real precedent exists of a previously-working captive portal regressing purely from an OS
  update with no code change on the device side
  ([espressif/arduino-esp32#10330](https://github.com/espressif/arduino-esp32/issues/10330) —
  Android 14/Samsung S23 stopped popping up between Arduino-ESP32 v2.x and v3.x; iOS unaffected;
  root cause in that specific case turned out to be an unrelated DNS-server-startup ordering bug in
  that library, not something applicable here, but the *regression exists independent of firmware
  code* precedent is the relevant takeaway).
- **Relative vs. absolute redirect target**: no source found any evidence that an absolute IP
  Location header is required or more reliable than a relative one for plain-HTTP captive portals
  (the one documented downside of an absolute IP — breaking wildcard/TLS cert hostname matching —
  is an HTTPS-only concern and doesn't apply here). **Decision: use a relative `Location: /`**, not
  an absolute IP — see §1.4 for why this also avoids needing a second new accessor.
- DNS TTL: this repo's own `captive_dns.py` already hardcodes 60s (`\x00\x00\x00\x3c` in
  `DNSQuery.response()`), which lines up with the commonly-cited 0-60s range for captive-portal DNS
  answers. No source flagged TTL as a real lever for this specific bug. **No change needed.**

### 1.4 Project-wide code facts (this session's own read of the current code)

- `ext/microdot.py` (vendored, **never edited**) already exports a ready-to-use top-level
  `redirect` callable (`ext/microdot.py:1569`, `redirect = Response.redirect`), same pattern as the
  already-imported `abort`/`send_file` (`asy_webserver_service.py`'s existing
  `from microdot import Request, abort, send_file`). `Response.redirect(location, status_code=302)`
  (`ext/microdot.py:762`) only raises `ValueError` if `location` contains `\r`/`\n` — impossible for
  a hardcoded literal `"/"`. **No vendored-file changes needed at all.**
- `WebserverService.__init__` (`asy_webserver_service.py:184-220`) is already an all-keyword,
  all-defaulted signature except `app` — confirmed by two existing call sites that pass only
  `app, static_mount="/html"` (`tests/test_website_build_integration.py:56`,
  `tests/test_frozen_html_integration.py:59`) and a third that forwards arbitrary `**kwargs`
  (`tests/test_asy_webserver_service.py:256`). **A new optional keyword parameter is fully
  backward-compatible with every existing call site — none need touching.**
- `AsyConnTime` (`src/asy_wifi_service.py`) tracks the connection phase in `self._conn_phase`
  (`_PHASE_STA_SEEKING` / `_PHASE_STA_ESTABLISHED` / `_PHASE_HOTSPOT` / `_PHASE_DEACTIVATED`,
  lines 61-65). **No existing accessor is equivalent to "is hotspot active":**
  `network_available()` (line 684) is `False` during both hotspot *and* ordinary STA-seeking, so it
  can't be reused to distinguish them. A new one-line accessor is needed (§3).
- `network_available()`'s own comment says its caller must already hold `wifi_mode_lock` because it
  touches `self.wlan` via `_wlan_status_or_none()`. A pure `self._conn_phase` int-compare touches no
  hardware and needs no such discipline — confirmed by reading the surrounding lock-convention
  comment block (`asy_wifi_service.py:632-641`) that explicitly documents both getter shapes and
  says a new getter must pick one deliberately. **The new accessor is the lock-free,
  callable-from-anywhere shape**, matching `get_dns_server_ip()`/`get_wlan_rssi()`'s style, not
  `network_available()`'s.
- `own_ip` (the value actually handed to `captive_dns.py`'s `DNSServer.run(server_ip, netmask)` at
  `asy_wifi_service.py:319`) is a local variable inside `AsyConnTime`'s own hotspot-setup code, not
  exposed via any public getter today. **Choosing a relative redirect (`"/"`, §1.3) avoids needing
  to expose this value at all** — one fewer accessor, one fewer thing that could disagree with what
  `captive_dns.py` itself uses.
- `sensortask_wozi.py`'s `build_system()` constructs `conn = AsyConnTime(...)` first (line 308) and
  `webserver = WebserverService(...)` near the end (line 378) — the same relative order `ntp`
  already uses to receive three of `conn`'s bound methods as constructor arguments
  (`conn.get_wifi_mode_lock`, `conn.network_available`, `conn.get_dns_server_ip`, lines 316-318).
  **Wiring `is_hotspot_active=conn.is_hotspot_active` into the existing `WebserverService(...)` call
  is one more argument in an already-established pattern — no reordering.**
- `tests/test_digital_twin_webserver_concurrency.py`'s `_boot()` calls
  `sensortask_wozi.build_system(...)` directly (the real construction path), so once
  `sensortask_wozi.py` is updated, the digital twin automatically inherits the wiring — **no
  digital-twin-specific code change needed.**
- `tests_hardware/bench/test_network_resilience.py::test_get_nonsense_path_is_shaped_404_over_the_normal_network`
  already asserts the exact opposite behavior (`404`, shaped JSON, empty error log) for an unmatched
  path **on the normal STA network**. This is the load-bearing regression guard: the fix must be
  strictly additive for the hotspot-active case only, never change STA-mode behavior.
  `assert_module_error_log_empty(dut_ip, "WEBSERVER")` in that same test also constrains the
  hotspot-mode path: a routine redirect must **not** log a warning/error either (matches
  `_shaped_error_handler()`'s existing "a routine 404 must not show up as an error" convention —
  the new redirect path should follow the same convention, logging nothing).
- SPECIFICATION.md Part A.5 (confirmed by direct read, `SPECIFICATION.md:400-489`) establishes that
  **every exception raised inside a route handler is already caught by Microdot itself** per
  request (`dispatch_request()`'s blanket `except Exception`), converted to a shaped 500 and logged
  via the already-registered `@app.errorhandler(Exception)`. `_serve_static()` runs inside that
  handler chain (called from the `_get_static`/`_get_static_index` route handlers). **This means a
  hypothetical exception from calling `is_hotspot_active()` needs no bespoke try/except of its own
  — it's already safely contained.** (See §2 for why this resolves a design question rather than
  leaving it open.)
- Part G's cross-language mirror rule (`SPECIFICATION.md:3406-3410`) only applies when new code has
  *both* a `src/` and a `js/` side. This change is pure server-side HTTP-fallback routing with no
  `js/` counterpart — the browser/OS handles the redirect natively during captive-portal browsing,
  before any of this project's own JS ever loads. **Confirmed not applicable; no `js/`/`tests_js/`
  changes.**
- No existing config-schema/settings-group field resembles a "captive portal enabled" toggle
  (checked the `"networking"` settings group registered in `sensortask_wozi.py`'s
  `WebserverService(..., settings={...})` call). This behavior is mode-driven and automatic (like
  the DNS spoofer itself, which has no on/off setting either) — **no new config field.**

---

## 2. Design decisions already resolved (do not re-litigate)

1. **Redirect, not serve-content.** Return `redirect("/")` (302) from the unmatched-path fallback,
   not `index.html` content directly. Reasoning: matches the more modern/robust reference
   implementations (§1.2); keeps the change to the *fallback* only, with zero touch to the
   file-serving path that already works; lands the client back on the existing `_get_static_index`
   route for the actual page render, so there is exactly one code path that renders the portal
   page, not two.
2. **Relative `"/"` target, not an absolute IP.** See §1.3/§1.4 — no evidence it's needed, and it
   avoids exposing a second new accessor for the device's own AP IP.
3. **Gated by a new `AsyConnTime.is_hotspot_active()` accessor**, lock-free (plain
   `self._conn_phase == _PHASE_HOTSPOT` read), passed into `WebserverService.__init__` as an
   **optional** keyword parameter (default `None`, meaning "always 404" — i.e. exactly today's
   behavior). This makes the change purely additive: any call site that doesn't pass it (every
   existing one) is byte-for-byte unaffected.
4. **No defensive try/except around calling `is_hotspot_active()`** inside `_serve_static()` — Part
   A.5 already guarantees any exception there is safely caught and shaped by Microdot's own
   blanket per-request handler (§1.4). Do not add a redundant guard; it would just be dead code
   Part G's "reuse, don't reimplement" principle would flag.
5. **DHCP Option 114: out of scope for this unit of work** (§1.3). If the project owner wants it
   tracked, it's a BACKLOG.md future-idea line, not part of this implementation.
6. **No legacy `python/CommonDrivers/` changes.** The identical 404-not-redirect gap almost
   certainly exists in the deployed pre-refactor webserver too, but CLAUDE.md's hard rules scope
   this refactor's work to `src/`; touching `python/` needs its own severity-justified exception,
   which a UX nice-to-have doesn't meet. **Flag this as a discussion point for the project owner in
   the implementing session's own report-back — do not silently fix or silently skip it.**
7. **No `js/`/`tests_js/` changes** (§1.4, Part G mirror rule doesn't apply here).
8. **No new config/settings field** (§1.4).

---

## 3. Exhaustive action list

### 3.1 `src/asy_wifi_service.py`

Add one new method near `network_available()`/`get_dns_server_ip()`/`get_wlan_rssi()`
(the lock-free getter group, per the file's own documented convention at lines 632-641):

```python
def is_hotspot_active(self) -> bool:
    return self._conn_phase == _PHASE_HOTSPOT
```

No lock check needed (pure int compare, no hardware touch) — but add a short comment saying so
explicitly, matching this file's own existing practice of documenting *why* a getter picked its
shape (the block at 632-641 already asks for this).

### 3.2 `src/asy_webserver_service.py`

- Import `redirect` alongside the existing `abort`/`send_file`:
  `from microdot import Request, abort, redirect, send_file`.
- Add a `TYPE_CHECKING`-only type alias next to the existing `StatusSourceFct`/`MaintenanceFct`/etc.
  block (lines ~46-50): `HotspotActiveFct = Callable[[], bool]`.
- `WebserverService.__init__`: add `is_hotspot_active: "HotspotActiveFct | None" = None` to the
  keyword-argument list (placement: near `static_mount`/`static_index`, the two params it's
  logically paired with — both only matter when `static_mount is not None`). Store as
  `self._is_hotspot_active = is_hotspot_active`.
- `_serve_static()`: change the `except OSError:` branch from unconditional `abort(404)` to:
  ```python
  except OSError:  # no such file in the mounted filesystem ...
      if self._is_hotspot_active is not None and self._is_hotspot_active():
          return redirect("/")
      abort(404)
  ```
- Update the module's own docstring/header comment and the `_serve_static`/`_get_static` inline
  comments to describe the new hotspot-mode fallback (module header is capped at 3 lines per
  CLAUDE.md's working agreements — keep additions to inline comments, not the header block, unless
  the 3-line header genuinely needs a one-clause update).

### 3.3 `src/sensortask_wozi.py`

Add one keyword argument to the existing `WebserverService(...)` call (line ~378):
`is_hotspot_active=conn.is_hotspot_active,` — placed near `static_mount=`/`static_index=` if those
appear in this call, for readability (check current call site content for exact placement; if
`static_mount`/`static_index` aren't passed here at all, place it near `sensors=`/`settings=`
instead, whichever the existing ordering convention favors).

### 3.4 No other `src/`/`ext/`/`js/`/config files change.

### 3.5 Documentation updates (after implementation is verified, not before)

- `SPECIFICATION.md` Part A.5: add a short bullet describing the new hotspot-mode redirect fallback
  and its exception-safety rationale (mirrors this doc's §1.4/§2.4 reasoning, condensed).
- `SPECIFICATION.md` Part A.7 (construction order) if it enumerates `WebserverService(...)`'s
  arguments in detail (it does, `SPECIFICATION.md:562-570`) — add the new argument to that
  enumeration.
- `tests_hardware/README.md`'s "Known assumptions and open findings" list: add an entry once the
  real-hardware test (see §5) has actually run and the behavior is confirmed on real hardware, not
  before — follow this repo's own "flag as unverified until actually run" convention used
  throughout that file.
- This file (`CAPTIVE_PORTAL_HOTSPOT_REDIRECT_PLAN.md`): delete once the above migrations are done,
  per its own lifecycle note at the top.
- Optional: a `BACKLOG.md` line for DHCP Option 114 as a deferred future idea (§2.5) — project
  owner's call whether it's worth tracking at all.

---

## 4. Regression / impact analysis

| Area | Impact | Why safe |
|---|---|---|
| STA-mode unmatched-path 404 | **None** | `is_hotspot_active` is `False` outside `_PHASE_HOTSPOT`; fallback behavior is byte-for-byte unchanged. Directly guarded by the existing `test_get_nonsense_path_is_shaped_404_over_the_normal_network`. |
| Matched static file routes (`/`, real assets) | **None** | Change is only in the `except OSError` fallback branch; the `send_file(...)` success path is untouched. |
| Matched API routes (`/sensors`, `/measurements`, `/networking`, ...) | **None** | Microdot's `find_route()` matches registered exact routes before ever reaching `/<path:filename>`'s catch-all (existing registration-order comment, `asy_webserver_service.py:276-283`) — this change lives entirely inside that catch-all's own fallback, never reached for a real route. |
| Every existing `WebserverService(...)` call site (`tests/test_website_build_integration.py`, `tests/test_frozen_html_integration.py`, `tests/test_asy_webserver_service.py`, `tests_hardware/bench/test_network_resilience.py`'s indirect use via `sensortask_wozi.py`) | **None** | New constructor parameter is optional with a behavior-preserving default (`None`). |
| Digital twin (`digital_twin/`, `tests/test_digital_twin_*`) | **None required** | Twin boots through the real `sensortask_wozi.build_system()`, inheriting the wiring automatically; no separate twin-side change. Twin's fake `network.py` does not need to simulate `_PHASE_HOTSPOT` for existing twin tests to keep passing (they don't exercise this path today) — but see §5 for whether new twin-side coverage is worth adding. |
| Timing/WDT (`CLAUDE.md`'s "long-blocking operations" principle) | **None** | The added check is one synchronous int compare, no `await`, no lock acquisition — same cost class as the routes it sits beside. |
| Error/log volume (`assert_module_error_log_empty` convention) | **None** | `redirect()` cannot raise for a hardcoded `"/"` literal; no new log line is added on this path, matching the existing "a routine 404 must not show up as an error" convention that must now also hold for "a routine hotspot-mode redirect must not show up as an error." |
| Legacy `python/CommonDrivers/` | **Unchanged, deliberately** | Out of scope per Hard Rules; flagged to project owner, not silently fixed or silently ignored. |
| `js/`/website frontend | **None** | No code path in this project's own JS is involved in captive-portal browsing; Part G's cross-language mirror rule doesn't apply (§1.4). |

**Net assessment: this is a strictly additive change** — one new optional constructor parameter, one
new accessor method, and one new branch inside an existing exception-fallback path. Nothing existing
is modified in a way that changes its observable behavior.

---

## 5. Open items for the implementing session

These are genuine judgment calls left open deliberately (per CLAUDE.md's "flag genuinely ambiguous
decisions" agreement), not oversights:

1. **Real-phone popup verification is inherently manual** — no automated test can observe a phone's
   OS-level notification UI. Decide whether to (a) leave this purely as a manual verification step
   noted in `REAL_HARDWARE_RUN_LOG.md` once the automated redirect test passes, or (b) also add a
   `tests_hardware/manual/` script that guides a human through it (mirroring the existing
   `manual/` subpackage's purpose). Recommendation: (a) is enough — the redirect response itself
   (302 + `Location: /`) is the thing worth automated-testing; the OS popup is a consequence this
   project can't observe programmatically either way.
2. **Whether digital-twin coverage is worth adding** for the hotspot-redirect branch specifically
   (twin's fake `network.py` would need to simulate reaching `_PHASE_HOTSPOT`, which may or may not
   already be exercised by existing twin WiFi-fallback tests — check `digital_twin/network.py` and
   `tests/test_digital_twin_*wifi*`/`*hotspot*` before deciding whether this is free coverage or a
   real addition). If cheap, worth adding for the "digital-twin-e2e" CI job's own sake; if it
   requires twin-side network-simulation changes disproportionate to this fix's size, unit + real
   hardware coverage (§6) is already sufficient and this can be skipped.
3. **BACKLOG.md entry for DHCP Option 114**: add or don't, project owner's call (§2.5) — not
   blocking for this PR either way.

---

## 6. Test plan (staged: plain functionality → stability/no crashes → max coverage)

### Stage 1 — plain functionality (unit level, real MicroPython Unix-port interpreter)

- `tests/test_asy_wifi_service.py`: new cases for `AsyConnTime.is_hotspot_active()` — `True` only
  when `_conn_phase == _PHASE_HOTSPOT`; `False` in `_PHASE_STA_SEEKING`, `_PHASE_STA_ESTABLISHED`,
  and `_PHASE_DEACTIVATED` (all four phases, not just two — this is exactly the kind of "systematic
  false-negative" gap SPECIFICATION.md Part E.5 warns about: testing only the True case and one
  False case would miss a regression in, say, `_PHASE_DEACTIVATED`).
- `tests/test_asy_webserver_service.py`: new cases in the static-route section —
  - `is_hotspot_active=lambda: True` + unmatched path → `302`, `Location: /` header present and
    exactly `"/"`.
  - `is_hotspot_active=lambda: False` + unmatched path → unchanged shaped `404` (regression guard,
    mirrors the existing hardware-tier test's assertion at the unit level too).
  - `is_hotspot_active=None` (constructor default, i.e. every pre-existing call site's behavior) +
    unmatched path → unchanged shaped `404` (the actual backward-compatibility guarantee, tested
    directly, not just inferred).
  - A real static file request (`/`, and a real mounted asset) still succeeds (`200`) regardless of
    `is_hotspot_active`'s value in either direction — confirms the fallback branch is never reached
    for a real hit.
  - A real API route request (e.g. `/sensors`) is unaffected regardless of `is_hotspot_active`'s
    value — confirms the catch-all fallback never shadows a registered route.

### Stage 2 — stability / no crashes / no raises

- Run the *entire* existing `tests/test_asy_webserver_service.py` and `tests/test_asy_wifi_service.py`
  suites and confirm 100% pass — direct regression gate on everything else those files already
  cover (connection hardening, settings dispatch, error shapes, etc. — none of it should be
  touched by this change, but prove it rather than assume it).
- Confirm `redirect("/")` genuinely never raises in this call shape (already established from
  reading `ext/microdot.py` directly, §1.4 — write the test anyway so the guarantee is enforced by
  CI, not just narrative).
- A `is_hotspot_active` callable that itself raises (simulate with a lambda that raises inside a
  test) → confirm the *existing* Microdot blanket-catch machinery converts it to a shaped 500 and
  logs it via the already-registered `@app.errorhandler(Exception)` — proving §2.4's "no bespoke
  try/except needed" decision is actually correct, not just asserted.
- Full `scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh` clean run (CLAUDE.md's standing
  "every scope stays fully clean" bar) — zero findings expected, any nonzero result is a real
  regression per CLAUDE.md's own pre-push verification section.

### Stage 3 — max coverage

- `scripts/test.sh --coverage`: confirm both new branches inside `_serve_static()`'s `except
  OSError:` block (the `is_hotspot_active()` True path and the unchanged False/None path) are
  actually hit by Stage 1's tests, not just the method existing — check the coverage report
  directly rather than assuming test presence implies branch coverage (this is a non-gating report
  per CLAUDE.md, but still worth eyeballing for this specific new code).
- `tests_hardware/bench/`: 
  - Keep `test_get_nonsense_path_is_shaped_404_over_the_normal_network` unchanged and green
    (real-hardware regression proof for STA mode).
  - Add a new real-hardware test that drives the DUT into hotspot mode (reuse whatever mechanism
    `tests_hardware/bench/test_hotspot_role_reversal.py`/`test_wifi_networking.py` already use to
    force/observe that transition — don't invent a second way) and asserts a GET to a nonsense path
    returns `302` with `Location: /`, and that `assert_module_error_log_empty(dut_ip, "WEBSERVER")`
    still holds afterward (matching the STA-mode test's own "a routine response must not log an
    error" assertion, applied to the new code path).
- Manual verification (§5, item 1): once the automated hotspot-mode redirect test passes on real
  hardware, do one real phone join (Android and iOS if both available) and visually confirm the
  "Sign in to network" popup now appears, noting the result in `REAL_HARDWARE_RUN_LOG.md`. This is
  the one part of the whole feature no automated test can observe — call it out as such rather than
  silently skipping it or falsely claiming automated coverage proves the popup itself works.

---

## 7. Process reminders for the implementing session

- Follow CLAUDE.md's step-session workflow (refine scope → clarifying questions if any remain →
  tests first → implementation → coverage pass → **stop and report back**, don't merge or expand
  scope unilaterally). This document already completes that workflow's step 1 (scope) and most of
  step 2 (open questions are enumerated in §5, not hidden) — start from step 3 (write the Stage-1
  tests first, TDD, against §6).
  - **Whenever a new test file is added to `src/`/`tests/`, run CLAUDE.md's required bird's-eye
    scan** over the whole of `src/` (and re-check Part G's catalog/grep-for-the-shape step) before
    calling this done — this document already did that scan for this specific change (§1.4), but
    the implementing session should re-confirm nothing else in `src/` has drifted since this plan
    was written.
- This is a pure `src/`/`tests/`/`tests_hardware/` change — no `pyproject.toml`, `scripts/`, or
  `toolchain/versions.toml` edits, so CLAUDE.md's chroot-based "Pre-push verification" recipe is
  **not required** for this PR. Standard CI (`.github/workflows/ci.yml`) is sufficient.
- Target the pull request at `claude/digital-twin-oserror-7y00lb` (this plan's parent branch, itself
  PR'd against `main` as PR #50), not `main` directly — same pattern as the earlier
  `claude/unit-tests-future-ideation` spinoff (merged back via PR #52). Subscribe to the new PR's
  activity immediately after opening it, per the standing PR-babysitting rules.
- Delete this file (§3.5) as part of the same PR once its content has been migrated into
  `SPECIFICATION.md`/`tests_hardware/README.md`.

---

## Sources

- [p-doyle/Micropython-DNSServer-Captive-Portal](https://github.com/p-doyle/Micropython-DNSServer-Captive-Portal)
- [CDFER/Captive-Portal-ESP32](https://github.com/CDFER/Captive-Portal-ESP32)
- [Nordesems/esp-captive-portal](https://github.com/Nordesems/esp-captive-portal)
- [foxblock/esp-captive-portal](https://github.com/foxblock/esp-captive-portal)
- [espressif/arduino-esp32#10330 — captive portal regression on Android 14](https://github.com/espressif/arduino-esp32/issues/10330)
- [micropython discussion #12012 — redirect all requests to index.html](https://github.com/orgs/micropython/discussions/12012)
- [micropython discussion #9264 — captive portal / walled garden access via Pico W](https://github.com/orgs/micropython/discussions/9264)
- [technicalnoodles/captive-portal — DHCP Option 114 / RFC 8910 & 8908 reference implementation](https://github.com/technicalnoodles/captive-portal)
- [espressif/arduino-esp32#11399 — DHCP option 114 for captive portal](https://github.com/espressif/arduino-esp32/issues/11399)
