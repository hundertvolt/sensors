#!/usr/bin/env bash
# Runs a hardware pytest selection and judges it from its run record (scripts/_hardware_verdict.py):
# a plain exit code cannot see an unexpected skip or a gate deselection. Evidence (log, record) lands
# in build/archive/<runner>/<ts>/ (<runner> sanitised to [a-z0-9_]), each runner's newest three kept.
set -uo pipefail  # not -e: pytest's exit code is captured and judged, never fatal here
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

usage() {
    cat <<'EOF'
Usage: scripts/_require_clean_hardware_run.sh --runner NAME --levels TEXT [--marker-floor EXPR] [--not-clean-reason TEXT] [pytest args]

  --runner NAME            the runner the summary block names; its evidence archive is NAME
                           lowercased, every character outside [a-z0-9_] made _
  --levels TEXT            the summary block's Levels: line
  --marker-floor EXPR      the runner's own marker selection; a caller's -m narrows it, never replaces it
  --not-clean-reason TEXT  report a passing run as NOT CLEAN (exit 4), naming why
  -h, --help               this text

Other arguments are passed to pytest, before its -v. pytest keeps only its last -m, so it gets one:
-m "(FLOOR) and (EXPR)" for the caller's last -m EXPR, printed before the run. Exit: pytest's own code
when nonzero, else the verdict's (0 pass, 1 fail, 4 not clean); 2 for a usage error.
EOF
}

runner="" levels="" marker_floor="" not_clean_reason=""
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --runner|--levels|--marker-floor|--not-clean-reason)
            [ $# -ge 2 ] || { echo "error: $1 needs a value" >&2; usage >&2; exit 2; }
            case "$1" in
                --runner) runner="$2" ;;
                --levels) levels="$2" ;;
                --marker-floor) marker_floor="$2" ;;
                *) not_clean_reason="$2" ;;
            esac
            shift 2 ;;
        *) break ;;
    esac
done
if [ -z "$runner" ] || [ -z "$levels" ]; then
    echo "error: --runner and --levels are required" >&2
    usage >&2
    exit 2
fi
# The caller's last -m EXPR (or -mEXPR) narrows the floor inside one combined -m; every other argument passes as given.
pytest_args=() caller_markexpr=""
while [ $# -gt 0 ]; do
    case "$1" in
        -m)
            [ $# -ge 2 ] || { echo "error: -m needs a marker expression" >&2; usage >&2; exit 2; }
            caller_markexpr="$2"
            shift 2 ;;
        -m?*) caller_markexpr="${1#-m}"; shift ;;
        *) pytest_args+=("$1"); shift ;;
    esac
done
markexpr="${marker_floor:-$caller_markexpr}"
if [ -n "$marker_floor" ] && [ -n "$caller_markexpr" ]; then
    markexpr="($marker_floor) and ($caller_markexpr)"
fi
[ -z "$markexpr" ] || pytest_args+=(-m "$markexpr")

archive_name="${runner,,}"
archive_name="${archive_name//[^a-z0-9_]/_}"
# One retried sync before the run, then --no-sync on every uv call: an implicit sync would put a third-party fetch
# inside a hardware run.
if ! scripts/uv_sync_retried.sh; then
    echo "error: the retried uv sync failed - its output above names the cause; nothing reached the board" >&2
    exit 1
fi
if ! EVIDENCE_DIR="$(uv run --no-sync scripts/_archive_evidence.py --runner "$archive_name" --new-dir)" || [ ! -d "$EVIDENCE_DIR" ]; then
    echo "error: could not create the evidence directory under build/archive/$archive_name/" >&2
    exit 1
fi
export EVIDENCE_DIR  # the evidence helper saves a run's saved files beside its log and record
log="$EVIDENCE_DIR/pytest.log"
record="$EVIDENCE_DIR/run_record.json"

: >"$log"
[ -z "$markexpr" ] || printf '== Marker selection: -m "%s"\n' "$markexpr" | tee -a "$log"
PYTHONPATH=scripts uv run --no-sync pytest -p _pytest_run_record --run-record="$record" "${pytest_args[@]}" -v 2>&1 | tee -a "$log"
pytest_exit="${PIPESTATUS[0]}"

verdict_args=(--run-record "$record" --pytest-exit "$pytest_exit" --runner "$runner" --levels "$levels")
if [ -n "$not_clean_reason" ]; then
    verdict_args+=(--not-clean-reason "$not_clean_reason")
fi
uv run --no-sync scripts/_hardware_verdict.py "${verdict_args[@]}"
exit $?
