#!/bin/bash
# shards.sh <tag>: the three put-matrix shards one after another from wt-u23L, each alone in its own netns at nice 19;
# waits while more than 4 heavy processes run on the host. One line per shard to u23/lead2/shards_<tag>.txt.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
out=$S/u23/lead2/shards_$1.txt; : > "$out"
for n in 1 2 3; do
  while [ "$($S/u23/lead2/heavy.sh | head -1 | cut -d= -f2)" -gt 4 ]; do sleep 5; done
  r=$(PUT_MATRIX_SHARD=$n/3 $S/u23/lead2/vt.sh pm_$1_s$n tests_js/live-backend-put-matrix.test.js | tr '\n' ' ')
  dur=$(sed 's/\x1b\[[0-9;]*m//g' $S/u23/lead2/pm_$1_s$n.log | grep -E '^ +Duration' | head -1)
  echo "shard $n/3: $r |$dur" >> "$out"
done
echo done >> "$out"
