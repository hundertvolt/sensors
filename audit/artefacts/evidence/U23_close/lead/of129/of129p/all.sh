#!/bin/bash
# all.sh: every check of the OF-129 print edit on wt-u23w, one run at a time: checks.sh, then the unit file at -1, 32768
# and settrace, then the twin modes file at -1 and 32768, each started only while at most 3 other heavy processes run.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of129p
heavy() { ps -eo args= | grep -E -c '^(/root/pico-toolchain/micropython/ports/unix/build-[a-z]+/micropython|node .*vitest|[^ ]*python[0-9.]* -m (pytest|mypy)|[^ ]*/mypy )' ; }
wait_room() { while [ "$(heavy)" -gt 3 ]; do sleep 5; done; }
$O/checks.sh
for st in e f cov; do $O/one.sh wt-u23w after "$st" test_asy_wifi_service; done
for st in e f; do wait_room; echo "heavy before twin $st: $(heavy)" >> $O/summary.txt; $O/one.sh wt-u23w after "$st" test_digital_twin_wifi_modes; done
echo "all done" >> $O/summary.txt
