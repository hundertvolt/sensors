#!/bin/bash
# lane.sh <worktree> <lane> <jobfile>: each "phase stage file [prefix]" line through one.sh, ONE at a time in this
# worktree (tests/_tmp is per worktree: CONCURRENCY rule 4), each started only while the host runs at most 3 heavy.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of111
wt=$1; lane=$2
while read -r phase stage file prefix; do
  [ -z "$phase" ] && continue
  until [ "$($O/heavy.sh | head -1 | cut -d= -f2)" -le 3 ]; do sleep 5; done
  if [ -n "$prefix" ]; then WT=$wt LANE=$lane PREFIX=$O/$prefix $O/one.sh "$phase" "$stage" "$file"; else WT=$wt LANE=$lane $O/one.sh "$phase" "$stage" "$file"; fi
done < "$3"
echo "lane $lane done"
