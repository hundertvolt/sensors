#!/bin/bash
# stream.sh <tree> <phase> <listfile>: runs each "<test_x> <stage>" line of listfile through one.sh, one at a time.
O=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/of129
n=$(grep -c . "$3")
python3 "$O/runs.py" start "stream-$2" "$1" "u23/of129/stream.sh pid $$: $n file runs ($(basename "$3")), one at a time, each via one.sh in its own unshare -n, nice 19"
while read -r t stage; do
  [ -n "$t" ] && "$O/one.sh" "$1" "$2" "$stage" "$t"
done < "$3"
python3 "$O/runs.py" done "stream-$2" "(exited; see u23/of129/results.tsv)"
echo "STREAM DONE $1 $2" >> "$O/results.tsv"
