#!/bin/bash
# mc_gen.sh NAME FILE[:DEVICE]...: a merge check on the cwd's tree - the named test files at both stages (mc_files.sh),
# the whole tests_scripts tier, lint_direct and the six mypy passes; summary in S/u35/lead/mc_NAME/summary.txt, rc 1 on any red line.
[ -c /dev/null ] || exit 9
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
name_="${1:?}"; shift
O="$S/u35/lead/mc_$name_"
rm -rf "${O:?}"; mkdir -p "$O"
"$S/u35/lead/mc_files.sh" "$O" "$@"
PICO_TOOLCHAIN_DIR="$S/tc-int" timeout 3600 python -m pytest -q -p no:cacheprovider tests_scripts > "$O/tier.log" 2>&1
echo "tier rc=$? $(tail -1 "$O/tier.log")" >> "$O/summary.txt"
python3 -I audit/b3/raising_walk.py "$PWD" audit/b3/raising.md --check > "$O/walk.log" 2>&1
echo "walk rc=$? $(tail -1 "$O/walk.log")" >> "$O/summary.txt"
python3 -I audit/sweeps/e51_sweep.py --check > "$O/e51.log" 2>&1
echo "e51 rc=$? $(tail -1 "$O/e51.log")" >> "$O/summary.txt"
python3 -I audit/sweeps/review_rows.py --check > "$O/review_rows.log" 2>&1
echo "review_rows rc=$? $(tail -1 "$O/review_rows.log")" >> "$O/summary.txt"
"$S/u35/lead/lint_direct.sh" > "$O/lint.log" 2>&1
echo "lint_direct rc=$?" >> "$O/summary.txt"
ln -sfn "$S/shared/typings" typings
for pass in "main:" "twin:--config-file digital_twin/typecheck.ini" "host:--config-file host_typecheck.ini" \
    "bench_conftest:--config-file host_typecheck.ini tests_hardware/bench/conftest.py" "network:tests/network.py" \
    "conftest:--config-file host_typecheck.ini tests_scripts/conftest.py"; do
  pn="${pass%%:*}"; args="${pass#*:}"
  # shellcheck disable=SC2086
  mypy --cache-dir "$O/mypy_$pn" $args > "$O/mypy_$pn.log" 2>&1
  echo "mypy $pn rc=$? $(tail -1 "$O/mypy_$pn.log")" >> "$O/summary.txt"
done
link="$PWD/typings"
[ -L "$link" ] && rm "${link:?}"
grep -q "rc=[^0]" "$O/summary.txt" && exit 1
grep -q "markers=[^0]" "$O/summary.txt" && exit 1
exit 0
