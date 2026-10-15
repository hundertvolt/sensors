#!/bin/bash
# queue.sh <jobfile>: runs each "phase stage file [prefix]" line through one.sh, at most two at once, a job started
# only while the host's heavy count is at most 3 (so at most 4 run with it: every test file is wall-time bound).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of111
pids=()
while read -r phase stage file prefix; do
  [ -z "$phase" ] && continue
  while true; do
    alive=(); for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive+=("$p"); done; pids=("${alive[@]}")
    heavy=$($O/heavy.sh | head -1 | cut -d= -f2)
    if [ "${#pids[@]}" -lt 2 ] && [ "$heavy" -le 3 ]; then break; fi
    sleep 5
  done
  if [ -n "$prefix" ]; then PREFIX=$O/$prefix $O/one.sh "$phase" "$stage" "$file" & else $O/one.sh "$phase" "$stage" "$file" & fi
  pids+=("$!")
  sleep 3
done < "$1"
wait
echo "queue $1 done"
