# Six owner questions: B7 (LED) and B8 (build chain) (lead, 2026-11-03)

Prepared at the owner's request (2026-11-03 20:05 UTC: "Prepare these 5 questions and the one before that we can go
through them one by one"); asked one at a time. Each was checked by the lead against the tree at d6bc7617 and the
rulings file: none was decided before.

## 1. The notification's `State` field (B7 item 7)

Facts: before the audit the notification block on `/status` had `Triggered` and `TS`. U22 (01032838, 2026-10-13) added
`State`, shown as "Evaluation State" with a five-code table: 0 every signal evaluated; 1 not evaluated by setting
(AutoOn off, paused, outside the window); 2 no local time yet; 3 evaluated in part (a value unavailable); 4 the
service's own configuration unreadable. No owner request or approval is recorded; the approved `/status` list
(2026-10-02, "Sounds good") does not have it. No deployed unit has it.
- Remove: `/status` back to `Triggered` and `TS`; the row and its table go; an unreadable cycle leaves `TS` at the last
  good cycle, as before. Code 4 is W13 in the error counts, code 2 is `NTPSynced`, code 1 the owner's own settings, an
  unavailable value logs its sensor's error. About 25 lines in the service, one emitter line, the row and the table,
  and test scaffolding that boots all six devices.
- Keep: as is, code 3 then meaning only "a value unavailable" (the stale and non-numeric checks go in the same unit).
Touches: the notification service, `/status`, the Status page, the mock data. Recommendation: remove.
Answered (owner, 2026-11-03 20:35 UTC), after asking what the codes are about and whether the block was ever
requested: "As you said that code functionality can be tested without all that, we do as recommended, only keep
pause time": `Triggered`, `State` and `TS` go; `PauseTime` stays.

## 2. The boot entry's prints at DebugLevel 0 (B8 rows 6-7)

Facts: when an exception other than Ctrl-C ends the event loop, the generated `main.py` records reset reason 22 and
then prints the exception's traceback, at every DebugLevel (`buildgen/codegen.py:865-871`). That is console output at
level 0, against the owner's rule (2026-11-02 20:53: "There must be a mode which is really silent on the console,
ever. That's level 0."). The loop ends this way only if the supervisor itself fails; the next boot's `/status` shows
ResetReason 22 either way. Before the audit, `main.py` let the exception propagate, and MicroPython printed it.
- Drop the print: level 0 is silent; the reset reason stays the record; the traceback text is lost on every build.
  For debugging, the separately built no-autostart image is started by hand at the REPL, where an exception prints
  as usual. Removes the print and its scaffolding (a pre-bound variable, its comment, one lint exemption).
- Print only at level 1 and above: `main.py` would need the running logger's level, which lives inside `main()`'s
  objects (no early level read: the owner's (d2) answer of 2026-11-03), so the level has to be handed out to the entry.
  More code for a rare path.
- Re-raise, as before the audit: the interpreter prints the traceback at every level (the rule is still broken), and a
  `SystemExit` would soft-reset with no bus reset (SPECIFICATION.md F.5.4).
Also: the no-autostart image prints one line at import, the manual start command (OR86, owner 2026-09-28: "start it
manually in Thonny's REPL mode and watch the console logs"). That image exists only for starting by hand at the REPL.
Recommendation: drop the print; keep the no-autostart start line.
Answered (owner, 2026-11-03 20:40 UTC): "drop the traceback print and keep the start line, as you recommended".

## 3. The page's build-date stamp (B8 row 12)

Facts: added 2026-10-22 (656fc82f), no owner agreement recorded. A firmware build writes its date into the page as
`<meta name="build-date">`; the page compares it with the device's `BuildDate` and reloads if they differ. The page
already reloads when the device's build changes while it is open (agent 2026-09-30, owner-reviewed 2026-10-01), and
every page is served `Cache-Control: no-cache` (owner-reviewed 2026-10-02), so a reflashed device never serves a stale
page. The stamp only covers a reflash between the page loading and its first device check.
- Remove: the meta stamp, its read and compare in the page code, and its build steps (about 40 lines across the page
  code, the stager and the build scripts). `BuildDate` itself stays in GET /system and on the page.
- Keep: as is.
Touches: the website and its build. Recommendation: remove.
Answered (owner, 2026-11-03 20:43 UTC): "Remove it".

## 4. The "returned no JSON object" banner (B8 row 13)

Facts: added 2026-10-13 (9bf22747), no owner agreement recorded. When a GET answers 200 with JSON that is not an object
(a list, a number), the page shows an error banner "GET ... returned no JSON object". Before the audit it refused only
an empty body and used any other answer as the section's data. Every firmware GET route answers an object, so the
banner can never show from a device.
- Restore the pre-audit check: one refusal (empty body) and a typing cast. A non-object answer, which no device sends,
  would render as an empty section instead of a banner.
- Keep: as is.
Touches: the website's section loader. Recommendation: restore the pre-audit check.
Answered (owner, 2026-11-03 20:45 UTC): "Yes, restore".

## 5. A saturated error counter shown as "65535+" (B8 row 14)

Facts: added 2026-10-13 (9bf22747), no owner agreement recorded. Each module's error counter stops at 65535, as it did
before the audit (`print_log.py`'s `_MAX_CNT`). The page shows a counter at that cap as "65535+", so it does not read
as an exact count. A sensor failing every second reaches it in about 18 hours.
- Keep: one line and a constant, checked against the firmware's value by an existing test.
- Remove: the page shows "65535" for a counter that has stopped counting.
Touches: the error table's count column. Recommendation: keep.
Answered (owner, 2026-11-03 20:47 UTC): "Yes, that was a good addition, keep it".

## 6. Double stripes for Invalid and Failed Apply results (B8 row 15)

Facts: the Apply result is a coloured stripe on the card and on each field (owner, 2026-08-21, legacy's two levels). An
agent drew the stripe double for Invalid and Failed (2026-09-27), "so the state does not rest on colour alone"; no owner
review recorded. Before the audit all stripes were solid.
- Keep: a reader who cannot tell the colours apart still sees which fields failed. CSS only, four declarations.
- Restore solid: the state shows by colour alone.
Touches: the Settings pages' Apply feedback. Recommendation: keep.
Answered (owner, 2026-11-03 20:53 UTC): "No, don't keep it, it would make the page move strangely on errors,
color alone is fine.": solid stripes again. (Both forms are 3 px wide, so no layout shifts either way.)

## 7. A stopped SCD30 keeps driving the LED (B7 item 8, from the falsification, 2026-11-04)

Facts: before the audit, and in the deployed firmware, the notification evaluates each sensor's last stored value with
no regard to its age. An agent added a 3-hour age bound (`_SAMPLE_MAX_AGE_S`, 10,800 s); B7 removed it on the premise
that every sensor re-stamps its sample each cycle. The falsification refuted that for one case (probe P3): after
`PUT ContMeas false` the SCD30 stops measuring, its data-ready pin never rises, so no read cycle runs
(`asy_scd30_driver.py:434-449, 538-541`) and the last values (2000 ppm in the probe) stay stored with their old
timestamp; the notification then flashes red every FlashInterval, indefinitely. With the bound it stopped after 3 h.
- (a) As before the audit: nothing changes; AutoOn off stops the flashes.
- (b) Restore the 3 h bound: about 10 lines; flashes go on up to 3 h after the stop; a hardcoded time check.
- (c) At the source: once the SCD30 has missed two of its own measurement intervals (it already detects this and marks
  FRCState "not measuring", `:376-379`, `:440-444`), it publishes CO2, Temp, Hum, WetBulb and DewPoint as unavailable;
  the notification already skips an unavailable value. The website then shows the three readings as unavailable while
  the sensor is stopped, not the last values. One `_republish()` call in the SCD30 driver, plus its tests.
Touches: the notification (b), the SCD30 driver and the website's view of a stopped SCD30 (c). Recommendation: (c).
Answered (owner, 2026-11-04 05:28 UTC): "For the stopped sensor, option c, the clean solution": (c).
