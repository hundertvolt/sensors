# Wave-2 rulings (agent, 2026-10-13, under the owner's 2026-10-13 efficiency decision; they override the briefs)
1. Reading: `S/CHECKLIST.md` + your brief + only the rulings it cites. common.md and CONCURRENCY.md are reference only.
2. No WIP stop and no `audit/u24-api2`: D runs straight to its final. U1 keeps its local `BMP_EXPECTED_TEMPERATURE`
   mirror; the lead step replaces it with the import of D's constant (a pure migration, checked at both GC stages).
3. Timing: no before-runs. Base times are `S/u24/base_times.tsv` (every tests/ file at -1 and 32768 on <W1>, one
   timed sweep by the lead). Report after-times of the files you grew; >10 % slower is made efficient.
4. Hand-back <= 30 lines is the whole record (CHECKLIST "Hand-back").
5. F's item 8 (agent, 2026-10-13; a pinned-source fact, A-7's principle: a fake follows rp2 where its source decides):
   the unit UART fake models rp2's TX/RX pin rule (`ports/rp2/machine_uart.c:71-80, 314-323`). `tests/machine.py` moves
   to U3's set for exactly that edit (seen failing first); U3 then fixes `test_asy_uart_driver.py:178`'s invalid
   `UART(1, tx_pin=0, rx_pin=1)` and :245 turns green.
6. Wave-2 expected reds: F's per-file list (`S/u24/laneF/handback_F_all.md`, "Wave 2 reds the fakes caused" and the
   parked-only files) is each lane's starting list, rechecked on <W1>. U2 also owns the surface-check red on its
   doubles (`_FakeModule.set_calls`, `_FakeLogger.err_count`/`reset_calls` in test_asy_webserver_service.py).
   U2 fact: rp2 ignores the RTC weekday (machine_rtc.c:85-96); `asy_ntp_client.py:329`'s tm[6]+1 is harmless.
7. From H's final (639a6e4): `tests/rp2.py` (in no set; one const mirror) joins U3's set. `tests/_ntp_frames.py` moves to
   U2's set: its :37 treats any recvfrom OSError as a spurious wake-up (silent-failure class 4) -> only the expected
   timeout is absorbed, anything else raises, seen failing first. U1: test_voc_algorithm's `_FIELDS` only shares a name
   with a src/ const -> rename it (or pin it if it is a real mirror). Expected L0 reds per lane: H's hand-back
   (`S/u24/laneH/handback_H_all.md`, "Red until wave 2").
