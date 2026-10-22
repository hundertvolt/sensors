/**
 * Pure field-value formatting with no DOM dependency: templates.js puts its text into the page.
 * See SPECIFICATION.md Part H.8.1.
 */

import { GMTIME_KEYS } from "./api-contract.js";

// A narrow local shape: the formatter reads only these members; a real FieldDef satisfies it structurally.
/** @typedef {{kind: string, mask?: boolean, format?: string, decimals?: number, options?: {value: unknown, label: string}[], specialValues?: {value: unknown, meaning: string}[]} & Record<string, unknown>} FormattableField */
/** @typedef {{deviceNowS: number | null, defaultDecimals?: number | undefined}} FormatContext */

const INVALID_TIME_TEXT = "invalid time value";
const INVALID_VALUE_TEXT = "invalid value";
// A timestamp up to this far ahead of the page's estimate of the device clock reads as now: the
// estimate trails the device by a /status request's latency.
// @tunable web.clock_mismatch_s = 5
const CLOCK_MISMATCH_S = 5;

/**
 * @param {number} epochS a Unix timestamp
 * @param {unknown} deviceNowS the device's own Unix time, or null when it is not known yet
 * @returns {string} the timestamp's age against the device's clock
 */
function formatEpochAge(epochS, deviceNowS) {
    if (typeof deviceNowS !== "number") {
        return "age unknown";
    }
    const age = deviceNowS - epochS;
    if (age < -CLOCK_MISMATCH_S) {
        return "clock mismatch";
    }
    const ageS = Math.max(Math.floor(age), 0);
    if (ageS < 120) {
        return `${ageS} s ago`;
    }
    if (ageS < 7200) {
        return `${Math.floor(ageS / 60)} min ago`;
    }
    if (ageS < 172800) {
        return `${Math.floor(ageS / 3600)} h ago`;
    }
    return `${Math.floor(ageS / 86400)} d ago`;
}

/**
 * @param {unknown} value
 * @returns {string} `<Task> at uptime <Uptime> s` for a task-end record, or the invalid-value text.
 */
function formatTaskEnd(value) {
    // Real shape: LastTaskEnd in the generated module's _system_status() (buildgen/codegen.py).
    if (typeof value !== "object" || value === null) {
        return INVALID_VALUE_TEXT;
    }
    const { Task: task, Uptime: uptime } = /** @type {Record<string, unknown>} */ (value);
    return typeof task === "string" && Number.isInteger(uptime) ? `${task} at uptime ${String(uptime)} s` : INVALID_VALUE_TEXT;
}

/**
 * @param {unknown} value
 * @returns {string} `Y-MM-DD hh:mm:ss` read through GMTIME_KEYS, or the invalid-time text.
 */
function formatTimeStruct(value) {
    // Real shape: the generated module's _gmtimestruct_to_dict() (buildgen/codegen.py); Weekday/Yearday unused.
    if (typeof value !== "object" || value === null) {
        return INVALID_TIME_TEXT;
    }
    const members = GMTIME_KEYS.map((key) => /** @type {Record<string, unknown>} */ (value)[key]);
    if (!members.every((member) => Number.isInteger(member))) {
        return INVALID_TIME_TEXT;
    }
    const [year, ...rest] = members.map((member) => String(member).padStart(2, "0"));
    return `${year}-${rest[0]}-${rest[1]} ${rest[2]}:${rest[3]}:${rest[4]}`;
}

// The formats whose value is a JSON object, each read through its own shape check.
/** @type {Map<string | undefined, (value: unknown) => string>} */
const RECORD_FORMATTERS = new Map([
    ["gmtimestruct", formatTimeStruct],
    ["lasttaskend", formatTaskEnd],
]);

/**
 * @param {FormattableField} field
 * @param {unknown} value
 * @param {FormatContext} [context] the device's clock and the definitions' default decimals
 * @returns {string}
 */
export function formatFieldValue(field, value, context = { deviceNowS: null }) {
    const special = field.format === "epoch" ? (field.specialValues ?? []).find((candidate) => candidate.value === value) : undefined;
    if (special !== undefined) {
        return special.meaning;
    }
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
    const formatRecord = RECORD_FORMATTERS.get(field.format);
    if (formatRecord !== undefined) {
        return formatRecord(value);
    }
    const finite = typeof value === "number" && Number.isFinite(value);
    if (field.format === "epoch" && finite) {
        return formatEpochAge(value, context.deviceNowS);
    }
    // The `decimals` display hint, and the one place in the stack that rounds an emitted value: no
    // driver in src/ rounds anything, so without this a declared precision is an aspiration.
    // Finite numbers only - a string, struct, NaN or Infinity passes through untouched.
    if (finite && typeof field.decimals === "number") {
        return value.toFixed(field.decimals);
    }
    // The site default for a float with no decimals hint (owner, 2026-10-02: "limit to 2 or 3 digits behind
    // the decimal point, don't print full floats. But only for the website, the API delivers full resolution.").
    if (finite && !Number.isInteger(value) && typeof context.defaultDecimals === "number") {
        return value.toFixed(context.defaultDecimals);
    }
    if (Array.isArray(value)) {
        return value.length === 0 ? "none" : value.map(String).join(", ");
    }
    return String(value);
}
