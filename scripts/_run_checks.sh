#!/usr/bin/env bash
# _run_checks.sh [-d LOGDIR] STEP...: each named check from the repository root, one after another, its whole output in
# LOGDIR and here only its exit code, wall time and _log_verdict.py's reading of its log (.claude/skills/work-routines).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
logdir="${CHECK_LOG_DIR:-${TMPDIR:-/tmp}/sensors-checks}/$(date -u +%Y%m%dT%H%M%SZ)"
verdict_lines="${CHECK_VERDICT_LINES:-12}"

usage() {
    cat <<'EOF'
Usage: scripts/_run_checks.sh [-d LOGDIR] STEP [STEP ...]
  lint            scripts/lint.sh
  typecheck       scripts/typecheck.sh (all three mypy passes)
  unit            scripts/test.sh at gc -1
  unit-gc         GC_THRESHOLD=32768 scripts/test.sh
  cover           scripts/test.sh --coverage (its test result gates, its coverage figure does not)
  twin[:DEV]      scripts/run_digital_twin_ci.sh DEV, both GC stages and both parts (DEV default dev)
  npm             npm run lint, typecheck and test:unit
  collect         pytest --collect-only over tests_hardware (no board contact)
  fw[:DEV]        scripts/build_firmware.py DEV and its image size line (DEV default dev)
  mpy:FILE        one tests/test_*.py under the Unix port at gc -1, then at 32768 (set TEST_DEVICE if it needs one)
  py:ARGS         python -m pytest -q ARGS, e.g. 'py:tests_scripts/test_x.py -k name'
  -d LOGDIR       the logs' directory (default $CHECK_LOG_DIR, else $TMPDIR or /tmp, then sensors-checks/<UTC stamp>)
  -h, --help      print this help and exit
CHECK_VERDICT_LINES caps each step's verdict (12). unit, unit-gc, cover, twin and npm bind fixed ports, so another
session's run makes them refuse, naming it (scripts/_port_lock.sh). Exit 0 when every step passed, 1 when one failed,
2 on a usage error.
EOF
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    -d) [ -n "${2:-}" ] || { echo "error: -d needs a directory" >&2; exit 2; }; logdir="$2"; shift 2 ;;
    "") usage >&2; exit 2 ;;
esac
[ "$#" -gt 0 ] || { echo "error: no step given (scripts/_run_checks.sh --help lists them)" >&2; exit 2; }
for step in "$@"; do
    case "$step" in
        lint|typecheck|unit|unit-gc|cover|twin|twin:?*|npm|collect|fw|fw:?*|mpy:?*|py:?*) ;;
        *) echo "error: unknown step '$step' (scripts/_run_checks.sh --help lists them)" >&2; exit 2 ;;
    esac
done
if [ -n "${VIRTUAL_ENV:-}" ]; then py=(python); else py=(uv run --no-sync python); fi
mkdir -p "$logdir"
cd "$root"
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
require_python311

# mpy_file FILE STAGE: one Unix-port file at one GC stage, with scripts/test.sh's own binary, layout and heap size.
# shellcheck disable=SC2329  # invoked by name, through run_step
mpy_file() {
    local file="$1" stage="$2" bin path heap
    bin="$(scripts/_unix_port.sh unix_port_bin standard)" || return 3
    path="$(scripts/_unix_port.sh micropypath unit)" || return 3
    heap="$(grep -o -m 1 'heapsize=[0-9]*[KMG]' scripts/test.sh | cut -d= -f2)"
    [ -n "$heap" ] || { echo "error: scripts/test.sh passes no -X heapsize= to read"; return 3; }
    if [ ! -d build/generated_src ] || [ ! -f frozen_modules/frozen_html.py ]; then
        echo "error: generated inputs missing: one scripts/test.sh run builds both, or run"
        echo "'uv run scripts/_generate_sensortask_modules.py' and 'scripts/build_website.sh <device>'"
        return 3
    fi
    if [ "$stage" = "-1" ]; then
        env -u TEST_TWIN_HOST TZ=UTC MICROPYPATH="$path" "$bin" -X heapsize="$heap" "$file"
    else
        env -u TEST_TWIN_HOST TZ=UTC MICROPYPATH="$path" "$bin" -X heapsize="$heap" tests/_threshold_runner.py "$file" "$stage"
    fi
}

# run_step NAME COMMAND...: the command's output to its log, then one line of rc and wall time and the verdict.
failed=0
n=0
run_step() {
    local name="$1" log rc=0 t0
    shift
    n=$((n + 1))
    log="$logdir/$(printf '%02d' "$n")_$(printf '%s' "$name" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-80).log"
    t0=$(date +%s)
    "$@" > "$log" 2>&1 || rc=$?
    echo "$name rc=$rc $(( $(date +%s) - t0 ))s log=$log"
    { python3 "$here/_log_verdict.py" "$log" || true; } | sed 1d | head -n "$verdict_lines" | sed 's/^/  /'
    [ "$rc" -eq 0 ] || failed=1
}

for step in "$@"; do
    arg="${step#*:}"
    case "$step" in
        lint) run_step lint scripts/lint.sh ;;
        typecheck) run_step typecheck scripts/typecheck.sh ;;
        unit) run_step unit scripts/test.sh ;;
        unit-gc) run_step unit-gc env GC_THRESHOLD=32768 scripts/test.sh ;;
        cover) run_step cover scripts/test.sh --coverage ;;
        twin) run_step twin:dev scripts/run_digital_twin_ci.sh dev ;;
        twin:*) run_step "$step" scripts/run_digital_twin_ci.sh "$arg" ;;
        npm) run_step npm bash -c 'npm run lint && npm run typecheck && npm run test:unit' ;;
        collect) run_step collect "${py[@]}" -m pytest tests_hardware --collect-only -q -p no:cacheprovider ;;
        fw) run_step fw:dev "${py[@]}" scripts/build_firmware.py dev ;;
        fw:*) run_step "$step" "${py[@]}" scripts/build_firmware.py "$arg" ;;
        mpy:*) run_step "mpy-1:$arg" mpy_file "$arg" -1; run_step "mpy32768:$arg" mpy_file "$arg" 32768 ;;
        py:*) read -r -a pyargs <<< "$arg"; run_step "$step" "${py[@]}" -m pytest -q -p no:cacheprovider "${pyargs[@]}" ;;
    esac
done
exit "$failed"
