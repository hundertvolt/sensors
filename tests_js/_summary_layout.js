// npm test's side of the runner summary block (SPECIFICATION.md E.10): the items it files, as the NUL-separated records
// scripts/_summary_block.py, the one emitter, prints the block from. Pure, no Node built-ins: the reporter runs Python.

const KINDS = ["passed", "failed", "skipped", "deselected", "retried", "recovered", "vacuous"];

/**
 * @typedef {object} Summary
 * @property {string} runner
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
 * @param {string} [unit]
 * @returns {Summary}
 */
export function createSummary(runner, unit = "tests") {
    /** @type {Map<string, [string, string][]>} */
    const items = new Map(KINDS.map((kind) => [kind, []]));
    /** @type {[string, string][]} */
    const notes = [];
    return {
        runner,
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

/**
 * The block's records for `scripts/_summary_block.py --print`: each field ends in a NUL, items kind by kind.
 * @param {Summary} summary
 * @returns {string}
 */
export function summaryRecords(summary) {
    /** @type {string[][]} */
    const records = [["unit", summary.unit]];
    for (const [tag, value] of /** @type {const} */ ([["levels", summary.levels], ["gc", summary.gcStage], ["reason", summary.notCleanReason]])) {
        if (value !== null) {
            records.push([tag, value]);
        }
    }
    for (const [kind, list] of summary.items) {
        records.push(...list.map(([name, detail]) => ["item", kind, name, detail]));
    }
    records.push(...summary.notes.map(([name, text]) => ["note", name, text]));
    records.push(...summary.extraCounts.map(([unit, counts]) => ["counts", unit, ...KINDS.map((_kind, i) => String(counts[i] ?? 0))]));
    return records.flat().map((field) => `${field}\0`).join("");
}
