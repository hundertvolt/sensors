/**
 * Pure field-value formatting - split out of js/templates.js so a Node-context test harness can
 * reuse it with no DOM dependency. See SPECIFICATION.md Part H.8.1 for the full rationale.
 */

// Deliberately a narrow local shape, not `import("./definitions.js").FieldDef` - see
// SPECIFICATION.md Part H.8.1 for why. A real FieldDef object satisfies it structurally either way.
/** @typedef {{kind: string, mask?: boolean, format?: string, decimals?: number, options?: {value: unknown, label: string}[]} & Record<string, unknown>} FormattableField */

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
        // Real shape: the generated sensortask_<device> module's _gmtimestruct_to_dict() - {Year, Month,
        // MDay, Hour, Minute, Second, Weekday, Yearday} (the last two unused here), never a pre-formatted string.
        const t = /** @type {{Year: number, Month: number, MDay: number, Hour: number, Minute: number, Second: number}} */ (value);
        const pad = (/** @type {number} */ n) => String(n).padStart(2, "0");
        return `${t.Year}-${pad(t.Month)}-${pad(t.MDay)} ${pad(t.Hour)}:${pad(t.Minute)}:${pad(t.Second)}`;
    }
    // The `decimals` display hint, and the one place in the stack that rounds an emitted value: no
    // driver in src/ rounds anything, so without this a declared precision is an aspiration.
    // Finite numbers only - a string, struct, NaN or Infinity passes through untouched.
    if (typeof field.decimals === "number" && typeof value === "number" && Number.isFinite(value)) {
        return value.toFixed(field.decimals);
    }
    return String(value);
}
