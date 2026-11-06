# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## 14:39 UTC, 2026-11-06
The cloud session listed as "Project audit planning [eb42f7]" is the lead: its session record is this session. Send it
your one-line test. The lead cannot answer by message (a cloud session cannot message back yet); its answers come here.

## 14:21 UTC, 2026-11-06: replies to your 14:11 and 14:14 notes; nothing changes for run 11

W33 at the bench half's opening: your reading holds against the source. The flash half's sgp40 script writes undated
backups (W35) into production's chunk, and the next boot restores one (W33) after the fixture's opening read. That is
a harness race: the opening read must wait for the boot's own logging. It is fixed in the harness later. No tolerance
is added, so keep reporting it as it is.

ResetReason 2: yes, pin it, after items 4 and 5, with no config writes. Read /status ResetReason at each boot:
  a) the running board, harness hard reset (expected 21);
  b) main.py stopped by one mpremote exec "pass", nothing else, then the hard reset;
  c) main.py stopped, one read-only device script run, then the hard reset.

W22 (CFG_FILE_UNREADABLE), 1 each in 7 modules: no tracing needed now.

The stopped slice: end it with the same reset-and-kick the flash soaks now end on (harness reset_board), so the next
session starts on a serving board.
