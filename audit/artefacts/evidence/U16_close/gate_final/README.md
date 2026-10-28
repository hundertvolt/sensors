# U16 close gates

`first_37a88e6/`: the first close gate (lint, typecheck, test.sh at -1 and 32768, six twins, npm; its coverage leg was cut by
the harness time limit) with its three reds: the UART driver's retention test (-1), the boot-contiguity control on dev and a
variant literal (tests_scripts). `regate_d58b8dd/`: after the lead fixes and the U15 fix - every leg green but typecheck (the
twin pass's no-any-return in the twin FRAM test, fixed in ed5318a) and coverage (the FRAM erase test's scaffolding, fixed in
df48814). `final_df48814/`: lint, both typecheck scopes and the coverage suite on the final head, all green.
