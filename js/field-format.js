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
        // Real shape: src/sensortask_wozi.py's _gmtimestruct_to_dict() - {year, month, mday, hour,
        // minute, second, weekday} (weekday unused here), never a pre-formatted string.
        const t = /** @type {{year: number, month: number, mday: number, hour: number, minute: number, second: number}} */ (value);
        const pad = (/** @type {number} */ n) => String(n).padStart(2, "0");
        return `${t.year}-${pad(t.month)}-${pad(t.mday)} ${pad(t.hour)}:${pad(t.minute)}:${pad(t.second)}`;
    }
    // The `decimals` display hint - a sibling of `format` above, and the one place in the stack
    // that rounds an emitted value. No driver in src/ rounds anything (a hue arrives here as
    // 217.43859649122808), so without this a declared precision would be an aspiration rather
    // than a property. Numbers only, and finite ones: a string, a struct, NaN or an Infinity is
    // passed through untouched rather than being handed to toFixed().
    if (typeof field.decimals === "number" && typeof value === "number" && Number.isFinite(value)) {
        return value.toFixed(field.decimals);
    }
    return String(value);
}
