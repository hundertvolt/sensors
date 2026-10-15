Silent-failure scan, lane A files (working notes)

1. src/asy_base_classes.py SensorReader._trigger_loop(): boot arm failure (start_timers() runs before the
   tasks) is cleared and re-armed at the trigger task's first start; a successful re-arm leaves only the
   console line, nothing persisted. Class 6 (recovery not observable in the persisted log) / 4. Mode: boot,
   runtime limits (alarm pool ENOMEM). Covered by: the packet's text (A.U15.41) as written; NEW finding.
   Minimal fix: persist the stored error once before the re-arm (await self._timer_fault() then re-arm).
2. ThreadSafeFlag coalescing / dropped soft-Timer callback: a lost 1 s tick delays one read by <= 1 s;
   inherently bounded (C.9, F.1). Mode: load, scheduler queue full. No action.
3. BMP3XX ERR_REG conf_err (bit 2, clear-on-read) is read by every burst and discarded. Class 1. Mode:
   reconfiguration. DS002 limits conf_err to normal mode; the driver runs forced mode only, so it cannot be
   set (DS001 text silent). Inherently safe by mode; NEW note.
4. BMP3XX self-reset between the EVENT read and the conversion: one sample converted with the chip's
   defaults (still a valid compensated pressure), the next cycle re-applies. Class 5, bounded to one sample.
5. BMP3XX fatal_err persistently set: every cycle fails -> ladder -> give-up -> task restart loop ->
   supervisor ceiling -> reboot; visible (READ entries) and bounded. Covered (M.SRC_SENS.048 (1)).
6. BMP3XX compensation config unreadable: CFG_READ every cycle (FRAM-backed log write every cycle);
   pre-existing (was in _store_bmp()). Class 2-ish wear/churn, not silent. Existing.
7. Twin BMP3XX: 0xB6 does not reset OSR/CONFIG (U25), so an L2 chip-reset case cannot show a reverted
   setting being re-applied until U25. Class 3 (test tier). Covered at U25 (M.TWIN.010 reset values).
8. get_register_bytes() copies per cycle (EVENT 1 byte, burst 8 bytes): two small allocations per BMP cycle;
   accepted by OR110.a (3) until U30's own buffer. Mode: heap near full. Covered (U30).
Modes checked: boot, long uptime (tick wrap: _wait_status_bits unchanged, U14 crossing test green), NTP
unsynced/synced (TS None), bus down/wedged (OSError -> ladder), chip reset/brown-out (EVENT), heap near
full, FRAM absent/paused (logger), config write failing, load (PUT racing the rung, test).
