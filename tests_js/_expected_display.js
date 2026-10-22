// The text the page should show for a field's value, written apart from js/field-format.js so the live tier
// never checks the renderer against itself. Pure, no Node or DOM API: the Node command module and the browser
// test both import it (SPECIFICATION.md H.8.1).

/** @typedef {{kind: string, mask?: boolean, decimals?: number, options?: {value: unknown, label: string}[]}} DisplayField */

/**
 * `value` with exactly `decimals` digits after the point, rounded half away from zero by integer arithmetic.
 * @param {number} value
 * @param {number} decimals
 * @returns {string}
 */
function fixedPoint(value, decimals) {
    const digits = String(Math.round(Math.abs(value) * 10 ** decimals)).padStart(decimals + 1, "0");
    const whole = digits.slice(0, digits.length - decimals);
    const fraction = decimals > 0 ? `.${digits.slice(digits.length - decimals)}` : "";
    return `${value < 0 ? "-" : ""}${whole}${fraction}`;
}

/**
 * @param {DisplayField} field
 * @param {unknown} value
 * @param {number} [defaultDecimals] the definitions' `defaultDecimals`: a fraction's digits when the field names none
 * @returns {string}
 */
export function expectedDisplay(field, value, defaultDecimals) {
    if (value === null || value === undefined) {
        return "—";
    }
    if (field.mask === true) {
        return "••••••••";
    }
    if (field.kind === "enum") {
        return (field.options ?? []).find((option) => option.value === value)?.label ?? String(value);
    }
    if (typeof value === "number" && Number.isFinite(value)) {
        if (typeof field.decimals === "number") {
            return fixedPoint(value, field.decimals);
        }
        if (!Number.isInteger(value) && typeof defaultDecimals === "number") {
            return fixedPoint(value, defaultDecimals);
        }
    }
    return String(value);
}
