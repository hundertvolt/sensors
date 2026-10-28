#!/bin/bash
# Lane D: the given tests_scripts files one at a time at nice 19 from the given tree; a summary line each.
tree=$1; tag=$2; shift 2
out=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/laneD
cd "$tree" || exit 2
for f in "$@"; do
  s=$(date +%s.%N)
  PYTHONPATH=scripts nice -n 19 /home/user/sensors/.venv/bin/python -m pytest -q -p no:cacheprovider "tests_scripts/$f.py" > "$out/${tag}_$f.txt" 2>&1
  rc=$?
  printf '%s\t%s\trc=%s\t%.1fs\t%s\n' "$tag" "$f" "$rc" "$(echo "$(date +%s.%N) - $s" | bc)" "$(tail -n1 "$out/${tag}_$f.txt")"
done
