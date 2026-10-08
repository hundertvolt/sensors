#!/usr/bin/env bash
# Sourced emitter of the runner summary block (SPECIFICATION.md E.10); its Python twin
# scripts/_summary_block.py prints the same layout byte for byte.
(return 0 2>/dev/null) || { echo "error: source scripts/_summary_block.sh, do not run it" >&2; exit 2; }

_summary_kinds=(passed failed skipped deselected retried recovered vacuous)
_summary_kind=()
_summary_name=()
_summary_detail=()
_summary_extra=()
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
summary_result_reason() { _summary_reason="$1"; }

_summary_counts_text() {
    printf 'Counts (%s): passed %s · failed %s · skipped %s · deselected %s · retried %s · recovered %s · vacuous %s' "$@"
}

# summary_counts_line <unit> <passed> <failed> <skipped> <deselected> <retried> <recovered> <vacuous>
summary_counts_line() {
    if [ "$#" -ne 8 ]; then
        echo "error: summary_counts_line needs a unit and seven counts, got $# arguments" >&2
        return 2
    fi
    _summary_extra+=("$(_summary_counts_text "$@")")
}

_summary_count() {
    local kind="$1" n=0 k
    for k in "${_summary_kind[@]}"; do
        [ "$k" = "$kind" ] && n=$((n + 1))
    done
    printf '%s' "$n"
}

_summary_list() {
    local kind="$1" title="$2" i name detail any=0
    for i in "${!_summary_kind[@]}"; do
        [ "${_summary_kind[$i]}" = "$kind" ] || continue
        [ "$any" -eq 1 ] || printf '%s:\n' "$title"
        any=1
        name="${_summary_name[$i]}"
        detail="${_summary_detail[$i]}"
        if [ -z "$detail" ]; then
            printf '  - %s\n' "$name"
        elif [ "$kind" = "deselected" ]; then
            printf '  - %s: by %s\n' "$name" "$detail"
        elif [ "$kind" = "retried" ]; then
            printf '  - %s (attempt %s)\n' "$name" "$detail"
        else
            printf '  - %s: %s\n' "$name" "$detail"
        fi
    done
    [ "$any" -eq 1 ] || printf '%s: none\n' "$title"
}

_summary_notes() {
    local i
    if [ "${#_summary_note_name[@]}" -eq 0 ]; then
        printf 'Notes: none\n'
        return
    fi
    printf 'Notes:\n'
    for i in "${!_summary_note_name[@]}"; do
        if [ -z "${_summary_note_text[$i]}" ]; then
            printf '  - %s\n' "${_summary_note_name[$i]}"
        else
            printf '  - %s: %s\n' "${_summary_note_name[$i]}" "${_summary_note_text[$i]}"
        fi
    done
}

_summary_commit() {
    local sha porcelain
    if ! sha="$(git rev-parse --short HEAD 2>/dev/null)" || [ -z "$sha" ]; then
        printf 'unknown'
        return
    fi
    # A status git cannot report reads as dirty: an unknown tree is never presented as the commit.
    if ! porcelain="$(git status --porcelain 2>/dev/null)" || [ -n "$porcelain" ]; then
        printf '%s (uncommitted changes)' "$sha"
    else
        printf '%s' "$sha"
    fi
}

# summary_print <runner> <exit>: the block, last on stdout. It returns the code it printed, which the
# caller exits with: a failed or vacuous item raises a passing code (0, 3, 4) to 1, so the block and
# the process never disagree; a failure code (1, 2, any other) is kept.
summary_print() {
    local runner="$1" code="$2" result line failed vacuous
    failed="$(_summary_count failed)"
    vacuous="$(_summary_count vacuous)"
    if { [ "$failed" -ne 0 ] || [ "$vacuous" -ne 0 ]; } && { [ "$code" = "0" ] || [ "$code" = "3" ] || [ "$code" = "4" ]; }; then
        code=1
    fi
    if [ "$code" = "2" ]; then
        result="USAGE ERROR"
    elif [ "$failed" -ne 0 ] || [ "$vacuous" -ne 0 ]; then
        result="FAIL"
    elif [ "$code" = "0" ]; then
        result="PASS"
    elif [ "$code" = "3" ]; then
        result="PASS (coverage report not rendered)"
    elif [ "$code" = "4" ]; then
        result="NOT CLEAN"
        [ -z "$_summary_reason" ] || result="NOT CLEAN ($_summary_reason)"
    else
        result="FAIL"
    fi
    printf '== Summary: %s ==\n' "$runner"
    printf 'Commit: %s\n' "$(_summary_commit)"
    [ "$_summary_levels_set" -eq 0 ] || printf 'Levels: %s\n' "$_summary_levels_text"
    [ "$_summary_gc_set" -eq 0 ] || printf 'GC stage: %s\n' "$_summary_gc_text"
    printf '%s\n' "$(_summary_counts_text "$_summary_unit_name" "$(_summary_count passed)" "$failed" "$(_summary_count skipped)" "$(_summary_count deselected)" "$(_summary_count retried)" "$(_summary_count recovered)" "$vacuous")"
    for line in "${_summary_extra[@]}"; do
        printf '%s\n' "$line"
    done
    _summary_list failed "Failed"
    _summary_list skipped "Skipped"
    _summary_list deselected "Deselected"
    _summary_list retried "Passed only on retry"
    _summary_list recovered "Recovery passes"
    _summary_notes
    _summary_list vacuous "Checked nothing"
    printf 'Result: %s\nExit code: %s\n' "$result" "$code"
    return "$code"
}
