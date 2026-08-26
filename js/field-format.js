/**
 * Pure field-value formatting - split out of js/templates.js so a Node-context test harness can
 * reuse it with no DOM dependency. See WEBSITE_PLAN.md §6.1 for the full rationale.
 */

// Deliberately a narrow local shape, not `import("./definitions.js").FieldDef` - see WEBSITE_PLAN.md
// §6.1 for why. A real FieldDef object satisfies it structurally either way.
/** @typedef {{kind: string, mask?: boolean, format?: string, options?: {value: unknown, label: string}[]} & Record<string, unknown>} FormattableField */

/**
 * @param {FormattableField} field
 * @param {unknown} value
 * @returns {string}
 */
export function formatFieldValue(field, value) {
    if (value === undefined || value === null) {
        return "—";
    }
    if (field.mask === true) {
        return "••••••••";
    }
    if (field.kind === "enum") {
        const match = (field.options ?? []).find((option) => option.value === value);
        return match ? match.label : String(value);
    }
    if (field.format === "gmtimestruct") {
        // Real shape: src/sensortask_wozi.py's _gmtimestruct_to_dict() - {year, month, mday, hour,
        // minute, second, weekday} (weekday unused here), never a pre-formatted string.
        const t = /** @type {{year: number, month: number, mday: number, hour: number, minute: number, second: number}} */ (value);
        const pad = (/** @type {number} */ n) => String(n).padStart(2, "0");
        return `${t.year}-${pad(t.month)}-${pad(t.mday)} ${pad(t.hour)}:${pad(t.minute)}:${pad(t.second)}`;
    }
    return String(value);
}
