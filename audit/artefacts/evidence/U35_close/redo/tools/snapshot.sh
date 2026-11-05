#!/bin/bash
# snapshot.sh TREEISH PARENT MSGFILE: the tree of TREEISH plus the redo's records under the U35 evidence folder,
# committed on PARENT (the last pushed audit commit); prints the new commit. Pushing stays a separate step.
set -euo pipefail
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
TREEISH="$1"; PARENT="$2"; MSG="$3"
X=$S/u35/lead/snapshot_stage; R=$X/redo; P=audit/artefacts/evidence/U35_close
rm -rf "${X:?}"; mkdir -p "$R/tools"
cp -r $S/u35r/briefs $S/u35r/handbacks_redo $S/u35r/recovered $S/u35r/q35 "$R/"
rm -rf "$R/q35/__pycache__"
cp $S/u35r/REDO.md $S/u35r/owner_report_items.md $S/u35r/d3r_rec2_items.md $S/u35r/closing_ledger.md $S/CHECKLIST.md "$R/"
gzip -c $S/u35/lane_plan.md > "$R/lane_plan.md.gz"; gzip -c $S/u21/RUNS.md > "$R/RUNS.md.gz"
cp $S/u35/lead/run.sh $S/u35/lead/mc_gen.sh $S/u35/lead/mc_files.sh $S/u35/lead/lint_direct.sh $S/u35/lead/mc_tier.sh \
  $S/u35/lead/snapshot.sh $S/u23/rebuild.sh "$R/tools/"
cp $S/u35/lead/snap2/README.md "$X/README.md"
[ -d $S/u35r/scan_pub ] && cp -r $S/u35r/scan_pub "$X/scan"
[ -d $S/u35r/paused_pub ] && cp -r $S/u35r/paused_pub "$R/paused"
[ -d $S/u35r/plan ] && cp -r $S/u35r/plan "$R/plan"
[ -d $S/u35r/plancheck ] && (cd $S/u35r && tar --exclude=plancheck/falsify/f1work -cf - plancheck) | tar -xf - -C "$R"
[ -d $S/u35r/bench ] && (cd $S/u35r && tar -cf - bench) | tar -xf - -C "$R"
# fz/, ftmp/, xtmp/, probe/ and *_25c.py hold source and datasheet copies, trial_*.md merge trials, AGENT_IDS.txt the
# session's agent handles (never published); SNAP_EXCLUDE names a unit's unfinished files, space-separated.
EX=(--exclude='*.log' --exclude='*.out' --exclude='*.diff' --exclude=fz --exclude=ftmp --exclude=xtmp --exclude=probe
  --exclude='*_25c.py' --exclude='trial_*' --exclude=AGENT_IDS.txt --exclude='.*')
for e in ${SNAP_EXCLUDE:-}; do EX+=("--exclude=$e"); done
for d in r0 r1 r2 r3 knowledge findings; do [ -d $S/u35r/$d ] && (cd $S/u35r && tar "${EX[@]}" -cf - $d) | tar -xf - -C "$R"; done
[ -f $S/u35r/tools/review_hunks.py ] && cp $S/u35r/tools/review_hunks.py "$R/tools/"
[ -d $S/u35r/hw_handover ] && (cd $S/u35r && tar --exclude=hw_handover/logs --exclude=__pycache__ -cf - hw_handover) | tar -xf - -C "$R"
[ -f $S/u35r/int_history.txt ] && gzip -c $S/u35r/int_history.txt > "$R/int_history.txt.gz"
PAT="1234567[8]|192\.168\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+|ghp_[A-Za-z0-9]{10}|github_pa[t]_|sk-[A-Za-z0-9]{20}|AKIA[0-9A-Z]{12}|BEGIN [A-Z ]*PRIVATE KEY"
if grep -rlE "$PAT" "$X" --include='*.md' --include='*.sh' --include='*.py' --include='*.tsv' --include='*.log' --include='*.json'; then echo "scan hit: not committed" >&2; exit 2; fi
for z in $(find "$X" -name '*.gz'); do if zcat "$z" | grep -qE "$PAT"; then echo "scan hit in $z: not committed" >&2; exit 2; fi; done
# A staged file holding a module's opening docstring line (this tree's or the pre-audit one's) is a source copy.
for t in "$TREEISH" 25caf528; do git ls-tree -r --name-only "$t" -- src | grep '\.py$' | while read -r m; do
  git show "$t:$m" | awk '/^"""/ && !d {print; d=1}'; done; done | awk 'length($0) > 30' | sort -u > "$X.heads"
if grep -rlFx -f "$X.heads" "$X"; then echo "source copy staged: not committed" >&2; exit 2; fi
export GIT_INDEX_FILE=$X/index
git read-tree "$TREEISH"
(cd "$X" && find redo scan README.md -type f 2>/dev/null | sort) | while read -r f; do
  m=100644; case "$f" in *.sh) m=100755;; esac
  git update-index --add --cacheinfo "$m,$(git hash-object -w "$X/$f"),$P/$f"
done
T=$(git write-tree)
git commit-tree "$T" -p "$PARENT" -F "$MSG"
