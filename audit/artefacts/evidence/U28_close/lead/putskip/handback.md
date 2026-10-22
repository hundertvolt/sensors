# Hand-back: the PUT-matrix skip agent (as received, condensed)

All six skips are named by `tests_js/_summary_reporter.js` (gate1b `npm_test.log` lines 640-646); the file was not run. The
three `ctx.skip(cond, note)` sites at 3e87082 are `tests_js/live-backend-put-matrix.test.js:259`, `:269` and `:400`; vitest's
`context.skip` throws `PendingError` (`run.BTlFXlnv.js:3358-3364`) and the runner records the test skipped with its note.

1-2. arzi `networking/identity/SSID` and `networking/dns/DNSFallback`: "no current value to resubmit" (`:259`, `:269`).
3-6. dev `sensors/BMP3XX/PresOvers` (option 1), `TempOvers` (option 1), `FiltCoeff` (option 0), `sensors/ISL29125/IRCompOffset`
(option 0): "the current option: the resubmit probe covers it" (`:400`).

Each live twin boots from a fresh config directory, so each field starts at its source default: SSID `""`
(`src/asy_wifi_service.py:66`), PresOvers/TempOvers 1, FiltCoeff 0 (`src/asy_bmp3xx_driver.py:106-108`), IRCompOffset 0
(`src/asy_isl29125_driver.py:155`). DNSFallback's source default is "8.8.8.8,1.1.1.1" (`src/asy_ntp_client.py:116`), but the
twin runner plants `DNSFallback = ""` (`digital_twin/run_generic_integration.py:735`,
`digital_twin/unixport/_offline_ntp_config.py:27`) so no run reaches public DNS.

The enum skips are intended (`:397-398`, REGISTER.md:193, SF-U6-08); SSID's is intended as a class (`:242-247`,
REGISTER.md:180). The move from 5 to 6 skips is arzi's DNSFallback: the planted `""` arrived in U25's `311aef8`; before, the
probe ran and passed with "8.8.8.8,1.1.1.1"; U25's record logged "6 skipped" with no note. The mock tier still checks
DNSFallback's Unchanged answer (`mockdata/samples.json:14`, `mock-server-put-matrix.test.js:119`). Proposed, not implemented:
seed SSID and DNSFallback with non-empty values in the matrix twin's config directory; pin the four enum skips as a named
expected-skip list the file asserts.
