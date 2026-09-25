# Harvest — SEC: Security

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 2, INVAR 4, MIRROR 1, LIMIT 6, RISK 22, ASSUME 1, SUPPRESS 5, DRIFT 2, NOTE 3 — 46 items.


## src/asy_dns_client.py

- **SEC.N001** ASSUME · `src/asy_dns_client.py:72` — "a stale/spoofed reply (wrong transaction ID)" —
  Spoof defence is the 16-bit `os.urandom(2)` txn id only. · related: SEC.T11 · [H01]

## src/asy_udp_socket.py

- **SEC.N002** LIMIT · `src/asy_udp_socket.py:9-10` — "Content-agnostic: never inspects datagram
  contents; mode=\"server\" source-address trust is the caller's concern." — No source validation at
  this layer; pushes it to NTP/DNS/captive DNS callers · related: SEC.T05 · [H02]

## src/asy_wifi_service.py

- **SEC.N003** SETTLED · `src/asy_wifi_service.py:50-53` — "defaulting to the hardcoded \"12345678\": a
  known, accepted-risk credential (CLAUDE.md's hard rules), made per-device configurable rather than
  removed or rotated" — Accepted-risk hotspot password · covered-by: SEC.T07 · [H02]
- **SEC.N004** LIMIT · `src/asy_wifi_service.py:198-201` — "PW/HotspotPW are real credentials, masked
  here (\"********\")" — Masked value round-trips into a PUT as a literal password · covered-by: NET.S16
  · [H02]
- **SEC.N005** RISK · `src/asy_wifi_service.py:384` — "self.wlan.config(essid=hostname,
  password=password) # HotspotPW, per-device configurable" — No explicit `security=`; auth mode is the
  cyw43 default · covered-by: NET.S20 · [H02]

## src/captive_dns.py

- **SEC.N006** LIMIT · `src/captive_dns.py:66-67` — "mode=\"server\" sockets receive from anyone...
  run() filters to the AP's own subnet before ever replying." — Only access control is a source-address
  subnet filter · related: SEC.T05 · [H02]

## ext/microdot.py

- **SEC.N007** RISK · `ext/microdot.py:804-806` — "Security note: The filename is assumed to be trusted.
  Never pass filenames provided by the user without validating and sanitizing them first." — Project
  passes the client-supplied `<path:filename>` (only a `..` substring check; opens the stream itself) ·
  related: REST.T07 · [H02]

## tests_hardware/bench/test_hotspot_role_reversal.py

- **SEC.N008** SETTLED · `tests_hardware/bench/test_hotspot_role_reversal.py:144-146` — "Documents the
  known, hardcoded weak credential - not something to silently \"fix\" here, per CLAUDE.md's
  credential-handling rule" — Accepted-risk credential, restated in test code. · related: SEC.T07 ·
  [H07]

## scripts/test.sh

- **SEC.N009** RISK · `scripts/test.sh:280-288` — "Granted fresh every invocation, for the reason
  run_digital_twin_ci.sh's identical grant gives (xattrs)" — `setcap cap_net_bind_service=+ep` (via sudo
  when non-root) on the Unix-port interpreter every run. · covered-by: SCR.S06 · [H09]

## scripts/run_digital_twin_ci.sh

- **SEC.N010** RISK · `scripts/run_digital_twin_ci.sh:39-47` — "Granted fresh every invocation because a
  cached toolchain archive does not carry xattrs" — `setcap` (sudo when non-root) on the interpreter for
  Run 7's port-53 DNS server. · covered-by: SCR.S06 · [H09]

## scripts/run_unix_port_integration.sh

- **SEC.N011** RISK · `scripts/run_unix_port_integration.sh:18, 24` — "--host 0.0.0.0 --port 8080
  (reachable from outside)" — Documented way to expose the twin on all interfaces; default fixed port
  8080. (low) · [H09]
- **SEC.N012** RISK · `scripts/run_unix_port_integration.sh:59-67` — "Granted fresh every invocation" —
  Third `setcap` site. · covered-by: SCR.S06 · [H09]

## toolchain/setup_toolchain.py

- **SEC.N013** RISK · `toolchain/setup_toolchain.py:110-118` — "print(f\"$ {' '.join(cmd)}\"" — Every
  command, including the bench AP password (:916-921), is echoed with full argv; output is buffered
  until exit and there is no timeout. · covered-by: TOOL.S01 · [H09]
- **SEC.N014** RISK · `toolchain/setup_toolchain.py:915-921` — "\"wifi-sec.pmf\", \"disable\"" — Bench
  AP runs WPA2-PSK with PMF disabled; password passed and printed in argv (:924). · covered-by: TOOL.S01
  · [H09]

## buildgen/validate.py

- **SEC.N015** RISK · `buildgen/validate.py:111-119` — "one outside _VAL_HOTSPOT_PW's own bounds is
  dropped at boot back to the shared default - which for this field is the password published in src/,
  on every device at once" — Shared hardcoded hotspot password is the fallback (accepted risk per
  CLAUDE.md). · related: GEN.T08 · [H09]

## devices/dev.toml

- **SEC.N016** RISK · `devices/dev.toml:7` — "hotspot_password = \"12345678\"" — Shared hardcoded
  hotspot password, identical in all six TOMLs (accepted risk; not to be changed without the owner). ·
  related: GEN.T08 · [H09]

## devices/wozi.toml

- **SEC.N017** RISK · `devices/wozi.toml:7` — "hotspot_password = \"12345678\"" — Shared hotspot
  password. · related: GEN.T08 · [H09]

## devices/arzi.toml

- **SEC.N018** RISK · `devices/arzi.toml:7` — "hotspot_password = \"12345678\"" — Shared hotspot
  password. · related: GEN.T08 · [H09]

## devices/klkizi.toml

- **SEC.N019** RISK · `devices/klkizi.toml:8` — "hotspot_password = \"12345678\"" — Shared hotspot
  password. · related: GEN.T08 · [H09]

## devices/grkizi.toml

- **SEC.N020** RISK · `devices/grkizi.toml:8` — "hotspot_password = \"12345678\"" — Shared hotspot
  password. · related: GEN.T08 · [H09]

## devices/schlafzi.toml

- **SEC.N021** RISK · `devices/schlafzi.toml:8` — "hotspot_password = \"12345678\"" — Shared hotspot
  password. · related: GEN.T08 · [H09]

## pyproject.toml

- **SEC.N022** SUPPRESS · `pyproject.toml:165-167` — "Documented accepted risk, decided by the project
  owner ... The webserver binds 0.0.0.0 deliberately." — Ignore S104 globally. · [H09]
- **SEC.N023** DRIFT · `pyproject.toml:168-169, 233-235` — "The three known, accepted sites are exempted
  per file below." — S105/S106 are exempted in eight files (src/asy_wifi_service.py,
  digital_twin/launch.py, tests/test_digital_twin_network_neopixel.py, four tests_hardware files,
  tests_scripts/test_buildgen_validate.py); CLAUDE.md names two real credential sites; all six device
  TOMLs also carry the password. · covered-by: CI.S08 · [H09]
- **SEC.N024** SUPPRESS · `pyproject.toml:304-305` — "\"digital_twin/launch.py\" = [\"S105\"]" —
  Credential-rule exemptions with no stated reason on these two lines (covered by the "copies of an
  accepted risk" framing below). (low) · covered-by: CI.S08 · [H09]
- **SEC.N025** SUPPRESS · `pyproject.toml:338-347` — "copies of an accepted risk, exempted per file" —
  S105/S106 on four tests_hardware files and tests_scripts/test_buildgen_validate.py. · covered-by:
  CI.S08 · [H09]

## .gitignore

- **SEC.N026** INVAR · `.gitignore:1-3, 84-89` — "never commit a real one" / "config_WIFI.cfg carries
  SSID/PW on a tree that has real ones - ignored so a `git add -A` after a validation run cannot commit
  one" — Only future commits are guarded; device scripts run host-side spill credential-bearing
  `config_*.cfg` into the repo root. · covered-by: SCR.S09 · [H09]

## tests_scripts/_toml_fixtures.py

- **SEC.N027** RISK · `tests_scripts/_toml_fixtures.py:27` — "\"hotspot_password\": \"12345678\"" — Base
  fixture carries the same literal as the shared default hotspot password (test data, not a secret;
  recorded for credential-consistency sweeps) (low) · related: HW.T11 · [H10]

## tests_scripts/test_buildgen_generate.py

- **SEC.N028** RISK · `tests_scripts/test_buildgen_generate.py:405-411` — "assert
  \"hotspot_password='12345678'\" in result.module_source" — Test pins the shared default hotspot
  password literal in wozi's generated module (accepted-risk credential; SEC consistency sweep) ·
  related: SEC.T04 · [H10]

## tests_scripts/test_tests_hardware_conftest_constants.py

- **SEC.N029** RISK · `tests_scripts/test_tests_hardware_conftest_constants.py:72-81` — "Both must agree
  or the join just fails." — Enforces that the bench's hardcoded hotspot password equals the shared src
  default and dev's TOML value — the accepted-risk shared credential is pinned in three places ·
  related: SEC.T07 · [H10]

## js/definitions.js

- **SEC.N030** MIRROR · `js/definitions.js:231-238` — "data = JSON.parse(inlinedEl.textContent ??
  \"\");" — the inlined path depends on scripts/build_website.sh escaping `<` inside the embedded JSON
  so a literal `</script` cannot close the tag early (SPECIFICATION.md:4538-4539) · related: WEB.T06 ·
  [H11]

## js/render.js

- **SEC.N031** LIMIT · `js/render.js:219-223` — "pollManager.request(putPath, { method: \"PUT\",
  headers: { \"Content-Type\": \"application/json\" }, ..." — state-changing PUTs (incl. SystemCmd
  reboot/bootloader, ResetErrors) carry no authentication or CSRF token; the posture rests on the server
  side · related: WEB.T08 · [H11]

## package.json

- **SEC.N032** RISK · `package.json:21` — "\"preview\": \"python3 -m http.server 8000\"" — fixed port
  8000, serving the repo root on all interfaces · covered-by: CI.S16 · [H11]

## eslint.config.js

- **SEC.N033** LIMIT · `eslint.config.js:13-119` — "const BUG_CATCHING_RULES = {" — no rule (e.g.
  `no-restricted-properties`/`no-restricted-syntax`) enforces H.4's "`textContent` only, never
  `innerHTML`" · covered-by: WEB.S17 · [H11]

## tests_js/templates.test.js

- **SEC.N034** INVAR · `tests_js/templates.test.js:502-570` — "XSS safety (standing guideline:
  textContent only, never innerHTML)" — test covers hostile labels/values/names only, not keys that
  reach selectors/ids/dataset · covered-by: WEB.S17 · [H11]

## SPECIFICATION.md Part A.8 (REST API endpoint reference, 571-625)

- **SEC.N035** LIMIT · `SPECIFICATION.md:603` — "`\"SystemCmd\": \"reboot\"|\"bootloader\"|\"mempause\"`
  (enum-validated; `mempause` duration fixed 300s)" — Unauthenticated destructive commands; fixed pause
  length. · related: SEC.T02 · [H12]

## SPECIFICATION.md Part H.4 — Architecture decisions table

- **SEC.N036** INVAR · `SPECIFICATION.md:4359` — "`textContent` only, never `innerHTML` — XSS-safe by
  construction." | Security rule with no lint enforcement. · covered-by: WEB.S17 · [H13]

## SPECIFICATION.md Part L.2 — Core design decisions

- **SEC.N037** RISK · `SPECIFICATION.md:6034-6036` — "the hotspot password is a per-device TOML field
  defaulting to the existing hardcoded `\"12345678\"` (accepted risk, CLAUDE.md)" — Accepted credential
  risk. · related: GEN.T08 · [H13]
- **SEC.N038** RISK · `SPECIFICATION.md:6040-6043` — "a value outside either field's schema bounds is
  dropped back to that shared default at boot rather than failing - for the password, back to the one
  published in `src/`" — Silent runtime fallback to the published password; build-time caps mitigate. ·
  related: GEN.T15 · [H13]

## CLAUDE.md

- **SEC.N039** INVAR · `CLAUDE.md:184-186` — "Don't touch `sensors/config.json`-equivalent files or
  commit any real credentials." — `.gitignore` covers per-device configs; everything else is convention.
  No history secret scan is part of any gate. · related: SEC.T12 · [H14]
- **SEC.N040** RISK · `CLAUDE.md:186-190` — "accepted risk (only exploitable by someone in physical WiFi
  range of a unit that's already lost its real WiFi)" — Hardcoded hotspot fallback password; the owner's
  direction is needed to change it. Per-file S105/S106 exemptions keep new sites detectable. ·
  covered-by: SEC.T07 (related SEC.T04) · [H14]
- **SEC.N041** DRIFT · `CLAUDE.md:186-188` — "present in both `python/CommonDrivers/async_connect.py`
  (deployed, pre-refactor) and `src/asy_wifi_service.py` (promoted)" — The same literal is also in all
  six devices/*.toml (`hotspot_password = "12345678"`, e.g. devices/dev.toml:7). It is per-device
  configurable as `HotspotPW` (src/asy_wifi_service.py:50-53) (low). · related: SEC.T04, GEN.T08, CI.S08
  · [H14]

## Commit messages (chronological)

- **SEC.N042** NOTE(SEC) · `commit 1a8049e / 0a3bb38 / 5878c64` — "Allow git push origin in the Claude
  Code permission allowlist ... Bash(curl -s http://*)" — Repo-committed Claude Code permission
  allowlist (push to origin, curl any http host). · status: done-in a02bfff ("Remove
  accidentally-committed .claude/settings.json"; no .claude/ dir in snapshot) | related: SEC.T* · [H17]
- **SEC.N043** SUPPRESS · `commit d7df22b` — "the three known, already-accepted sites are exempted
  individually (src/asy_wifi_service.py, digital_twin/launch.py,
  tests/test_digital_twin_network_neopixel.py)" — S105/S106 per-file exemptions for the hotspot
  credential. · tracked: pyproject.toml per-file-ignores, CLAUDE.md credential rule | related: SEC.T* ·
  [H17]
- **SEC.N044** SUPPRESS · `commit a346c15` — "S603/S607 ... S310 ... S112 ... S105/S106 for the five
  copies of the DUT's own hotspot fallback password ... RUF007 for device_scripts/" — tests_hardware
  per-file exemptions incl. five copies of the hotspot password. · tracked: pyproject.toml
  per-file-ignores | related: SEC.T* · [H17]
- **SEC.N045** NOTE(SECURITY-HYGIENE) · `commit 7aba427` — ".gitignore: root-level config_*.cfg ...
  config_WIFI carries SSID/PW on a tree that has real ones" — Host-side runs of device scripts spill
  credential files into repo root. · status: done-in 7aba427 (.gitignore) | related: SEC.T* · [H17]

## GitHub PRs and issues (hundertvolt/sensors)

- **SEC.N046** NOTE(SEC) · `https://github.com/hundertvolt/sensors/pull/107` — "The committed bench PSK
  is redacted in it." — Post-snapshot PR notes a committed bench PSK · covered-by: PROJECT_AUDIT_PLAN
  HW.T11 / SEC.T12 | - · [H17]
