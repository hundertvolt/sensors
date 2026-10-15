#!/usr/bin/env bash
# Freezes the merged HTML_SRC_DIRS trees into one module with the vendored, unmodified ext/freezefs (SPECIFICATION.md
# A.9): gzip -n, a pinned clock and a sorted walk make the archive byte-reproducible; the build time lives only in
# buildgen/version.py. The gzip tree stays in build/frozen_html/<name>/ (or $FROZEN_HTML_WORK_DIR) until the next build.
set -euo pipefail
usage='Usage: HTML_SRC_DIRS="dir ..." scripts/build_frozen_html.sh [output_path]'
case "${1:-}" in
    -h | --help)
        cat <<'EOF'
Usage: HTML_SRC_DIRS="dir ..." scripts/build_frozen_html.sh [output_path]
Freezes the merged HTML_SRC_DIRS tree into one module (default output: frozen_modules/frozen_html.py).

Environment:
  HTML_SRC_DIRS          required, a space-separated list of source directories (scripts/build_website.sh sets it)
  FROZEN_HTML_WORK_DIR   the gzip tree, wiped at the start and kept (default: build/frozen_html/<output name>)
EOF
        exit 0
        ;;
    -*)
        echo "error: unknown option $1 - $usage" >&2
        exit 2
        ;;
esac
if [ "$#" -gt 1 ]; then
    echo "error: at most one output_path, got $# arguments - $usage" >&2
    exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
read -r -a src_dirs <<<"${HTML_SRC_DIRS:?HTML_SRC_DIRS must name the source dir(s) - scripts/build_website.sh sets it}"
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
require_python311

for src_dir in "${src_dirs[@]}"; do
    if [ ! -d "$src_dir" ]; then
        echo "error: HTML_SRC_DIRS entry '$src_dir' is not a directory - fix: point it at an existing source tree" >&2
        exit 1
    fi
done
out_file="${1:-frozen_modules/frozen_html.py}"
mount_target="/html"
work="${FROZEN_HTML_WORK_DIR:-build/frozen_html/$(basename "$out_file" .py)}"

# Cleaned at the start of a build, never at its end: the tree stays for inspection.
rm -rf "$work"
mkdir -p "$work"
echo "== Gzip tree: $work"
for src_dir in "${src_dirs[@]}"; do
    cp -r "$src_dir"/. "$work"/
done
find "$work" -type f -exec gzip -9 -n {} +

# freezefs raises with a traceback on a served path ("/" + the relative path) of 255 or more characters
# (ext/freezefs/archive.py's MAX_FILENAME_LEN); the build names it first.
while IFS= read -r -d '' entry; do
    served="/${entry#"$work"/}"
    if [ "${#served}" -ge 255 ]; then
        echo "error: website path $served is ${#served} characters; freezefs allows at most 254 - fix: shorten it" >&2
        exit 1
    fi
done < <(find "$work" -mindepth 1 -print0)

mkdir -p "$(dirname "$out_file")"
rm -f "$out_file"

# ext/freezefs is an implicit namespace package, hence PYTHONPATH=ext. Its archive stamps the local time and numbers
# each file in its directory walk's order: both are pinned here (the epoch, a sorted walk) without editing ext/.
PYTHONPATH="ext${PYTHONPATH:+:$PYTHONPATH}" python3 -c '
import sys, time
import freezefs.archive as archive
time.localtime = lambda *_args: time.gmtime(0)
_glob = archive.glob
archive.glob = lambda *args, **kwargs: sorted(_glob(*args, **kwargs))
sys.argv[0] = "freezefs"
sys.exit(archive.main())
' "$work" "$out_file" --on-import mount --target "$mount_target" --overwrite always --silent

echo "Wrote $out_file (mounts at $mount_target on import)"
