Files: `src/asy_neopixel_driver.py`, `src/asy_notification_service.py`, the notification block of `buildgen/codegen.py`
and `buildgen/definitions.py`, `mockdata/samples.json`, and the generated `_notification_status()` of all six devices.
I read the layer below at the pin for each call: `extmod/asyncio/funcs.py`, `core.py`, `event.py`, `task.py`, the
`modasyncio.c` pairing heap, `py/objnamedtuple.c`, and the WS2812 datasheet.

**By site, class by class**

1. Ignored status: the WS2812 has none to read. `NeoPixel.write()` is one `machine.bitstream()` call with no result,
   and the datasheet's power-lost reset is detected by nobody. Covered by row 27's periodic rewrite.
   Inherently safe otherwise.
2. Bounded storage: none added. The stored sample gains one slot, with no ring and no queue.
3. Detection left to chance: a blanked pixel was fixed only by the next state change. Row 27 now bounds it at 300 s,
   tested under driven time.
4. Swallowed failures:
   - The overlay wait's `TimeoutError` is swallowed by design, since the timeout is the refresh.
   - `_check_one()`'s unevaluated paths returned `False`, a failure that looked like data. They now return `None` and
     surface as State 3 (rows 23 and F2).
   - The config-failure cycle stored nothing. It now stores State 4 (F2).
   - A stale producer sample counted as current. It is now unavailable, State 3 (row 23).
   - The default sink's `False` is still "no LED", already covered by SF-B2.
5. Windows:
   - Each overlay wake now allocates about 896 B (64-bit Unix) for its runner and waiter tasks. These are temporary,
     and the structural guard shows nothing is retained. The allocation catalog row is U30's (A-13).
   - An NTP step forward past a producer's last `TS` reads as stale until that producer's next sample, at most one of
     its intervals. It self-heals; inherently bounded.
   - A step backward gives a negative age, which counts as current.
6. Faults without self-healing:
   - An ended overlay or signal task restarts into a defined state (rows 22 and 27), tested at L1 including under a
     real supervisor.
   - A `MemoryError` inside the bounded wait ends the overlay task, the supervisor restarts it with one SYSTEM entry,
     and the restart re-applies the overlay. Inherently handled.
7. Asymmetric reporting:
   - `/status` now tells why nothing flashed (F4 and X3).
   - **New, minor:** the Status page labels `TS` "Last Trigger Timestamp" (`buildgen/definitions.py:701`). It is the
     last cycle's time, stored on every cycle and now on config-failure cycles too. A reader can take a State-4 or
     State-1 cycle's time for a trigger. No step owns the label, so it is not changed; proposed "Last Cycle Time",
     for D/E or the lead.

**By mode**

- **LED.**
  - Enabled and disabled: `set_wifi_led(False)` leaves the overlay off, so the refresh rewrites black.
  - Each Wi-Fi pattern: the hotspot, the client and the no-configuration pattern on a real pixel, the last of these new
    in X4.
  - The silent mode: dark through entry, a silent attempt's `_led_toggle()`/`_led_on()` and `LEDWifiOn`, lit at the
    link (row 44).
  - The overlay alone; a running signal (the refresh waits for the lock); a refused, queued or expired request (landed
    U9 tests).
  - A task restart of either LED task, and a blanked pixel (the refresh).

  No finding beyond the label above. **Pair noted:** notification ramps still play on the shared pixel during the Wi-Fi
  silent mode. A-5 reads "completely silent" as the Wi-Fi LED's own behaviour; the owner's review row (`REGISTER.md:583`)
  covers it.
- **Wi-Fi, as far as my files take part** (the state machine is W's):
  - STA seeking: toggles at 0.5 s, each a wake with a temporary allocation.
  - Established: steady.
  - Hotspot with and without a client: patterns.
  - Silent: dark.
  - Unreadable configuration: its pattern obeys `LEDWifiOn`.

  A task restart in each runs `_reset_wlan_connect_state()`'s `_led_off()`, then the initial LED config; the overlay
  task follows whatever the service last set. A settings change in each goes through `reconnect_wifi()`: the flash is
  cancelled, the LED is left as the cancel left it, and the next attempt's toggle redraws it within one 5 s loop. The
  generated hook's fresh flag is pinned on every device (X4). No finding.
- **Notification.**
  - Each State code is tested at L1, and codes 2 and 0 per device on `/status`.
  - A stale or missing producer gives 3. A busy LED gives W67 (landed). The default sink gives nothing, by design.
  - The monitor task dead between supervisor passes: State and TS keep the last cycle's values. TS's age and SYSTEM's
    task-end entry show it, so it is inherently visible.
  - A service whose every signal was refused at setup reports State 0 over zero signals. Its W44/W45 refusals are
    persisted at setup and show in errcount. Inherently visible; no change.
- **Long uptime and heap:** the per-wake allocation is collectable and nothing is retained. **Boot:** the overlay task's
  first write is the current overlay, black at boot. **Reconfiguration:** a `FlashInterval` change does not change the
  refresh period, which is fixed. Re-check trigger: the default `FlashInterval`, Part N.
