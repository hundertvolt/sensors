#!/usr/bin/env bash
# Sourced accumulator of the runner summary block (SPECIFICATION.md E.10): it files the items, and summary_print hands
# them to the one emitter, scripts/_summary_block.py, as NUL-separated records.
(return 0 2>/dev/null) || { echo "error: source scripts/_summary_block.sh, do not run it" >&2; exit 2; }

_summary_block_py="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_summary_block.py"
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source "${_summary_block_py%/*}/_require_python.sh"

_summary_kinds=(passed failed skipped deselected retried recovered vacuous)
_summary_kind=()
_summary_name=()
_summary_detail=()
_summary_counts=()
_summary_note_name=()
_summary_note_text=()
_summary_unit_name="files"
_summary_levels_text=""
_summary_levels_set=0
_summary_gc_text=""
_summary_gc_set=0
_summary_reason=""

# summary_add <kind> <name> [<detail>]; an empty kind is a missing verdict and files the item failed.
summary_add() {
    local kind="$1" name="$2" detail="${3:-}" known
    if [ -z "$kind" ]; then
        kind="failed"
        detail="no verdict"
    fi
    for known in "${_summary_kinds[@]}"; do
        if [ "$kind" = "$known" ]; then
            _summary_kind+=("$kind")
            _summary_name+=("$name")
            _summary_detail+=("$detail")
            return 0
        fi
    done
    echo "error: summary_add: unknown kind '$kind' (one of: ${_summary_kinds[*]})" >&2
    return 2
}

# summary_note <name> [<text>]: listed under Notes:, never counted and never changing the result.
summary_note() {
    _summary_note_name+=("$1")
    _summary_note_text+=("${2:-}")
}

summary_unit() { _summary_unit_name="$1"; }
summary_levels() { _summary_levels_text="$1"; _summary_levels_set=1; }
summary_gc_stage() { _summary_gc_text="$1"; _summary_gc_set=1; }
summary_result_reason() { _summary_reason="$1"; }  # code 3's or 4's reason; 3 alone has a default

# summary_counts_line <unit> <passed> <failed> <skipped> <deselected> <retried> <recovered> <vacuous>
summary_counts_line() {
    if [ "$#" -ne 8 ]; then
        echo "error: summary_counts_line needs a unit and seven counts, got $# arguments" >&2
        return 2
    fi
    _summary_counts+=("$@")
}

# summary_print <runner> <exit>: the block, last on stdout. It returns the code it printed, which the
# caller exits with: a failed or vacuous item raises a passing code (0, 3, 4) to 1, so the block and
# the process never disagree; a failure code (1, 2, any other) is kept.
summary_print() {
    local runner="$1" code="$2" i
    require_python311 || return 1
    {
        printf 'unit\0%s\0' "$_summary_unit_name"
        [ "$_summary_levels_set" -eq 0 ] || printf 'levels\0%s\0' "$_summary_levels_text"
        [ "$_summary_gc_set" -eq 0 ] || printf 'gc\0%s\0' "$_summary_gc_text"
        [ -z "$_summary_reason" ] || printf 'reason\0%s\0' "$_summary_reason"
        for i in "${!_summary_kind[@]}"; do
            printf 'item\0%s\0%s\0%s\0' "${_summary_kind[$i]}" "${_summary_name[$i]}" "${_summary_detail[$i]}"
        done
        for i in "${!_summary_note_name[@]}"; do
            printf 'note\0%s\0%s\0' "${_summary_note_name[$i]}" "${_summary_note_text[$i]}"
        done
        for ((i = 0; i < ${#_summary_counts[@]}; i += 8)); do
            printf 'counts\0%s\0%s\0%s\0%s\0%s\0%s\0%s\0%s\0' "${_summary_counts[@]:i:8}"
        done
    } | python3 "$_summary_block_py" --print "$runner" "$code"
}
