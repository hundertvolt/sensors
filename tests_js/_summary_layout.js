// The runner summary block's layout (SPECIFICATION.md E.10) for npm test, byte for byte the one
// scripts/_summary_block.sh and scripts/_summary_block.py print. Pure, no Node built-ins: the reporter
// supplies the commit; `node tests_js/_summary_layout.js '<json>'` renders a canned input for that check.

const KINDS = ["passed", "failed", "skipped", "deselected", "retried", "recovered", "vacuous"];
const TITLES = /** @type {const} */ ([["failed", "Failed"], ["skipped", "Skipped"], ["deselected", "Deselected"], ["retried", "Passed only on retry"], ["recovered", "Recovery passes"], ["vacuous", "Checked nothing"]]);

/**
 * @typedef {object} Summary
 * @property {string} runner
 * @property {string} commit
 * @property {string} unit
 * @property {string | null} levels
 * @property {string | null} gcStage
 * @property {string | null} notCleanReason
 * @property {[string, number[]][]} extraCounts
 * @property {Map<string, [string, string][]>} items
 * @property {[string, string][]} notes
 * @property {(kind: string, name: string, detail?: string) => void} add
 * @property {(name: string, text?: string) => void} note
 */

/**
 * An empty block for `runner`; `add()` files one item, and an empty kind is a missing verdict, filed failed;
 * `note()` lists one note, never counted and never changing the result.
 * @param {string} runner
 * @param {string} commit
 * @param {string} [unit]
 * @returns {Summary}
 */
export function createSummary(runner, commit, unit = "tests") {
    /** @type {Map<string, [string, string][]>} */
    const items = new Map(KINDS.map((kind) => [kind, []]));
    /** @type {[string, string][]} */
    const notes = [];
    return {
        runner,
        commit,
        unit,
        levels: null,
        gcStage: null,
        notCleanReason: null,
        extraCounts: [],
        items,
        notes,
        add(kind, name, detail = "") {
            const [filedKind, filedDetail] = kind === "" ? ["failed", "no verdict"] : [kind, detail];
            const list = items.get(filedKind);
            if (list === undefined) {
                throw new Error(`unknown summary kind ${JSON.stringify(kind)} (one of: ${KINDS.join(" ")})`);
            }
            list.push([name, filedDetail]);
        },
        note(name, text = "") {
            notes.push([name, text]);
        },
    };
}

/** @param {string} unit @param {number[]} counts the seven counters, in KINDS order */
function countsLine(unit, counts) {
    return `Counts (${unit}): ${KINDS.map((kind, i) => `${kind} ${counts[i] ?? 0}`).join(" · ")}`;
}

/** @param {string} kind @param {string} name @param {string} detail */
function itemLine(kind, name, detail) {
    if (detail === "") {
        return `  - ${name}`;
    }
    if (kind === "deselected") {
        return `  - ${name}: by ${detail}`;
    }
    return kind === "retried" ? `  - ${name} (attempt ${detail})` : `  - ${name}: ${detail}`;
}

/** @param {Summary} summary */
function failsOnItems(summary) {
    return (summary.items.get("failed")?.length ?? 0) + (summary.items.get("vacuous")?.length ?? 0) > 0;
}

/**
 * The code the block prints and the run exits with: a failed or vacuous item raises a passing code
 * (0, 3, 4) to 1; a failure code is kept.
 * @param {Summary} summary
 * @param {number} given
 * @returns {number}
 */
export function summaryExitCode(summary, given) {
    return failsOnItems(summary) && [0, 3, 4].includes(given) ? 1 : given;
}

/** @param {Summary} summary @param {number} exitCode */
function resultText(summary, exitCode) {
    if (exitCode === 2) {
        return "USAGE ERROR";
    }
    if (failsOnItems(summary)) {
        return "FAIL";
    }
    const byCode = new Map([[0, "PASS"], [3, "PASS (coverage report not rendered)"], [4, summary.notCleanReason ? `NOT CLEAN (${summary.notCleanReason})` : "NOT CLEAN"]]);
    return byCode.get(exitCode) ?? "FAIL";
}

/**
 * The E.10 block, ending in one newline, nothing after it; it prints summaryExitCode(), never a pass under a failed item.
 * @param {Summary} summary
 * @param {number} given the code the run would exit with
 * @returns {string}
 */
export function renderSummary(summary, given) {
    const exitCode = summaryExitCode(summary, given);
    const lines = [`== Summary: ${summary.runner} ==`, `Commit: ${summary.commit}`];
    if (summary.levels !== null) {
        lines.push(`Levels: ${summary.levels}`);
    }
    if (summary.gcStage !== null) {
        lines.push(`GC stage: ${summary.gcStage}`);
    }
    lines.push(countsLine(summary.unit, KINDS.map((kind) => summary.items.get(kind)?.length ?? 0)));
    lines.push(...summary.extraCounts.map(([unit, counts]) => countsLine(unit, counts)));
    for (const [kind, title] of TITLES) {
        const items = summary.items.get(kind) ?? [];
        lines.push(items.length > 0 ? `${title}:` : `${title}: none`);
        lines.push(...items.map(([name, detail]) => itemLine(kind, name, detail)));
        if (kind === "recovered") {
            lines.push(summary.notes.length > 0 ? "Notes:" : "Notes: none");
            lines.push(...summary.notes.map(([name, text]) => itemLine("note", name, text)));
        }
    }
    lines.push(`Result: ${resultText(summary, exitCode)}`, `Exit code: ${exitCode}`);
    return `${lines.join("\n")}\n`;
}

/**
 * The canned-input form: one JSON argument (runner, commit, unit, levels, gc_stage, not_clean_reason,
 * items as [kind, name, detail], extra_counts as [unit, counts], notes as [name, text], exit_code), the block on stdout.
 * @param {string} json
 * @returns {string}
 */
export function renderCannedInput(json) {
    const input = /** @type {{runner: string, commit: string, unit?: string, levels?: string | null, gc_stage?: string | null, not_clean_reason?: string | null, items?: [string, string, string][], extra_counts?: [string, number[]][], notes?: [string, string][], exit_code: number}} */ (JSON.parse(json));
    const summary = createSummary(input.runner, input.commit, input.unit ?? "tests");
    summary.levels = input.levels ?? null;
    summary.gcStage = input.gc_stage ?? null;
    summary.notCleanReason = input.not_clean_reason ?? null;
    summary.extraCounts = input.extra_counts ?? [];
    for (const [kind, name, detail] of input.items ?? []) {
        summary.add(kind, name, detail);
    }
    for (const [name, text] of input.notes ?? []) {
        summary.note(name, text);
    }
    return renderSummary(summary, input.exit_code);
}

// Run as a script under Node only; reached through globalThis so this file stays browser code.
const nodeProcess = Reflect.get(globalThis, "process");
if (Array.isArray(nodeProcess?.argv) && String(nodeProcess.argv[1]).endsWith("_summary_layout.js")) {
    nodeProcess.stdout.write(renderCannedInput(String(nodeProcess.argv[2])));
}
