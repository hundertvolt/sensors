#!/usr/bin/env bash
# _tidy.sh [--caches] [--check-logs DAYS] [--prune-worktrees]: what takes space in this tree and around it, and the only
# deletions it makes: caches, old check logs, dead worktree entries. Evidence, venv and toolchain are never touched.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
logs="${CHECK_LOG_DIR:-${TMPDIR:-/tmp}/sensors-checks}"
caches=0
log_days=""
prune=0

usage() {
    cat <<'EOF'
Usage: scripts/_tidy.sh [--caches] [--check-logs DAYS] [--prune-worktrees]
  (no option)        report only: free space, the regenerable folders' sizes, untracked files, worktrees, check logs
  --caches           delete __pycache__, .pytest_cache, .mypy_cache, .ruff_cache and tests/_tmp under this tree
  --check-logs DAYS  delete scripts/_run_checks.sh runs older than DAYS days (CHECK_LOG_DIR, else $TMPDIR or /tmp)
  --prune-worktrees  git worktree prune: drop the records of worktrees whose folder is already gone
  -h, --help         print this help and exit
Never deleted: build/archive and digital_twin_ci_logs (evidence), logs/, .venv, node_modules, typings, the toolchain.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --caches) caches=1 ;;
        --prune-worktrees) prune=1 ;;
        --check-logs)
            [[ "${2:-}" =~ ^[0-9]+$ ]] || { echo "error: --check-logs needs a number of days" >&2; exit 2; }
            log_days="$2"
            shift ;;
        *) echo "error: unknown argument '$1' (scripts/_tidy.sh --help)" >&2; exit 2 ;;
    esac
    shift
done
cd "$root"

echo "== free: $(df -P -h . | awk 'NR == 2 { print $4 }') on $(df -P . | awk 'NR == 2 { print $6 }')"
for dir in build build/archive digital_twin_ci_logs logs node_modules .venv typings frozen_modules tests/_tmp; do
    [ -e "$dir" ] && echo "   $(du -sh "$dir" 2> /dev/null | cut -f1)	$dir"
done
cache_list="$(find . \( -name .git -o -name .venv -o -name node_modules \) -prune -o -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -print 2> /dev/null || true)"
echo "   caches: $(printf '%s' "$cache_list" | grep -c . || true) folder(s)"
untracked="$({ git status --porcelain --untracked-files=normal 2> /dev/null || true; } | sed -n 's/^?? //p')"
echo "== untracked, not ignored: $(printf '%s' "$untracked" | grep -c . || true)"
printf '%s\n' "$untracked" | grep . | head -n 10 | sed 's/^/   /' || true
echo "== worktrees (\"prunable\": its folder is gone, --prune-worktrees drops the record)"
{ git worktree list 2> /dev/null || true; } | sed 's/^/   /'
if [ -d "$logs" ]; then
    echo "== check logs: $(find "$logs" -mindepth 1 -maxdepth 1 -type d | wc -l) run(s), $(du -sh "$logs" | cut -f1) in $logs"
fi

if [ "$caches" = 1 ]; then
    printf '%s\n' "$cache_list" | grep . | while read -r dir; do rm -rf -- "$dir"; done || true
    [ -d tests/_tmp ] && rm -rf -- tests/_tmp
    echo "== deleted the caches and tests/_tmp"
fi
if [ -n "$log_days" ] && [ -d "$logs" ]; then
    find "$logs" -mindepth 1 -maxdepth 1 -type d -mtime "+$log_days" -exec rm -rf -- {} +
    echo "== deleted check-log runs older than $log_days day(s)"
fi
if [ "$prune" = 1 ]; then
    git worktree prune --verbose
    echo "== pruned dead worktree records"
fi
