# Step 12 lead review (2026-10-07), for lane D's packet (step 80f)
- Accepted: classification.md sections A-E; 62 F.7 candidates in 15 groups, 132 into the "used by nothing here" sentence.
- The step text expects MICROPY_ASYNC_KBD_INTR to differ between the Unix builds; it does not: build_unix_port() applies
  the unix_kbd_intr override to both variants (0 in all three builds). F.7/E.5.2 text states the measured fact.
- Row 11 wording, verified at py/objexcept.c:478-505 and :207-250 (v1.29.0): rp2 enables the buffer with size 0
  (dynamic). Without a reserved buffer the message is lost only when the 16-byte str object or the 1-tuple cannot be
  allocated (args become the empty tuple, str(e) == ''); a failed text buffer alone keeps the ROM text. So "can be
  empty", not "is empty" (M.TSC.108's :12-14 comment and A.U14.05 say "without one it is empty": write it precisely).
  No alloc_emergency_exception_buf() call exists yet; A.U20.04 adds it (lane plan A-4).
- New groups beyond A.U14.28's rows 1-14 (ERROR_REPORTING NORMAL vs DETAILED, machine fakes, scheduler depth/printer,
  module loading, VFS, random seed, stack margin) become rows from 15 as the plan says.
