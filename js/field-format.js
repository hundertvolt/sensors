/**
 * Pure field-value formatting - deliberately split out of js/templates.js (the visual/DOM layer,
 * WEBSITE_PLAN.md §12) since this one function has zero DOM dependency and needs to run in a
 * Node context too: tests_js/_live_matrix_command.js (a server-side Vitest Commands API
 * implementation, not browser code) imports it directly to compute the exact rendered text a real
 * UI action should produce, without pulling js/templates.js's own `document`/`HTMLElement` surface
 * into that Node-context type-check program (tsconfig.node.json has no "dom" lib - importing the
 * whole file there produced dozens of unrelated errors, confirmed directly).
 */

// Deliberately NOT `import("./definitions.js").FieldDef`: js/definitions.js has its own
// HTMLElement-typed JSDoc elsewhere (loadDefinitions()'s inlinedEl param) - checkJs mode still
// full-type-checks a JSDoc-imported module even when only one of its exported types is used, so
// referencing the real FieldDef here would pull js/definitions.js into
// tests_js/_live_matrix_command.js's own Node-context type-check program too (this file is
// imported there - see this file's own header comment), which has no "dom" lib and would then
// fail on that unrelated HTMLElement reference (confirmed directly - that's exactly what happened
// before this comment existed). This narrower local shape covers everything formatFieldValue()
// itself actually reads; a real FieldDef object satisfies it structurally at runtime either way.
// Intersected with Record<string, unknown> (not just the bare shape) so a real FieldDef literal's
// extra properties (key, label, min, ...) don't trip TS's excess-property check at call sites that
// pass one directly (tests_js/templates.test.js does exactly this) - this type only *requires* the
// fields below, it was never meant to *forbid* every other real FieldDef property.
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
