/**
 * Loads and strictly validates a device's definitions.json (SPECIFICATION.md Part H.5). A shape/
 * version mismatch surfaces a visible error rather than silently rendering something broken or
 * skipping unknown fields (Part H.4's "Definitions validation").
 *
 * @typedef {{value: string|number, label: string}} EnumOption
 * @typedef {{value: number|string|null, meaning: string}} SpecialValue
 * @typedef {{
 *   key: string, label: string, unit?: string, kind: "readonly"|"number"|"string"|"enum"|"toggle"|"composite",
 *   description?: string, min?: number, max?: number, minLength?: number, maxLength?: number,
 *   mask?: boolean, options?: EnumOption[], specialValues?: SpecialValue[],
 *   subFields?: FieldDef[], onLabel?: string, offLabel?: string,
 *   format?: "gmtimestruct"|"epoch", float?: boolean, dispatch?: boolean, alwaysExecuted?: boolean,
 *   defaultValue?: unknown, path?: string[], decimals?: number, byteLength?: boolean,
 *   shape?: "hostLabel"|"countryCode", codes?: Record<string, string>,
 * }} FieldDef
 * @typedef {{key: string, label: string, fields: FieldDef[], submit?: boolean, submitLabel?: string}} FieldGroup
 * @typedef {{
 *   key: string, label: string, kind: "errcount", modules: {key: string, label: string}[],
 *   codes?: {E: Record<string, string>, W: Record<string, string>},
 * }} ErrcountGroup
 * @typedef {{
 *   key: string, label: string, description?: string,
 *   rest: {get: string, put?: string},
 *   pollGroup: "live"|"settings"|"none", pollIntervalMs?: number,
 *   groups: (FieldGroup|ErrcountGroup)[],
 * }} Section
 * @typedef {{
 *   schemaVersion: string, websiteVersion?: string, device: {id: string, displayName: string},
 *   landingSection: string, defaultPollIntervalMs: number, sections: Section[],
 * }} SiteDefinitions
 * @typedef {{
 *   measurements: Record<string, Record<string, unknown>>,
 *   sensorsConfig: Record<string, Record<string, unknown>>,
 *   networkingConfig: Record<string, unknown>,
 *   systemConfig: Record<string, unknown>,
 *   notificationConfig: Record<string, unknown>,
 *   status: {
 *     networking: Record<string, unknown>, system: Record<string, unknown>,
 *     sensors: Record<string, Record<string, unknown>>, notification: Record<string, unknown>,
 *     errcount: Record<string, {counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}>,
 *   },
 * }} MockDeviceData
 * @typedef {{
 *   measurements: Record<string, Record<string, unknown>>,
 *   sensorsConfig: Record<string, Record<string, unknown>>,
 *   networkingConfig: Record<string, unknown>,
 *   systemConfig: Record<string, unknown>,
 *   notificationConfig: Record<string, unknown>,
 *   status: {
 *     networking: Record<string, unknown>, system: Record<string, unknown>,
 *     sensors: Record<string, Record<string, unknown>>, notification: Record<string, unknown>,
 *   },
 *   errcount: Record<string, {counter: number, history: {num: number, type: "N"|"E"|"W"}[]}>,
 * }} MockSamples
 */

import { fetchWithTimeout } from "./poll-manager.js";

// float?: true marks a "number"-kind field whose real server-side type is Python float, not the
// int default (SPECIFICATION.md Part A.8) - tells coerceAndValidate() when a fractional value is
// actually valid.

// errcount history shape matches asy_print_log.py/asy_webserver_service.py exactly: no per-entry
// timestamp exists; "type" ("N"/"E"/"W") only colors "num" (a raw errno), never shown as text.

// dispatch?: true and alwaysExecuted?: true mark the two never-"Unchanged" classes
// (SPECIFICATION.md Part H.4); neverUnchanged() below reads them - never a key list.

// defaultValue is a field's safe synthetic baseline for when GET never reports a real value (a
// command with no persisted state, e.g. SCD30's ContMeas) - see resolveFieldValue() below.

/** The only schema major version this build of the renderer understands. */
export const SUPPORTED_SCHEMA_MAJOR = 1;

// Number#toFixed's own ceiling: a larger value would throw a RangeError in the card.
const MAX_DECIMALS = 100;

// The enumerated hint values the generator emits (buildgen/web_tag.py's _FORMATS and _SHAPES).
const FIELD_FORMATS = new Set(["gmtimestruct", "epoch"]);
const STRING_SHAPES = new Set(["hostLabel", "countryCode"]);

/**
 * True for the two classes the server never answers "Unchanged" (SPECIFICATION.md Part H.4).
 * @param {FieldDef} field
 * @returns {boolean}
 */
export function neverUnchanged(field) {
    return field.dispatch === true || field.alwaysExecuted === true;
}

// websiteVersion is build provenance only (SPECIFICATION.md Part L.7), distinct from
// schemaVersion's wire-format concern above. Nothing renders it - you always have exactly the
// build you fetched - so it is unvalidated too, and a bad value costs provenance, not rendering.

/**
 * A field's effective current value: the real value from `currentValues` when GET reported one,
 * otherwise `field.defaultValue`, otherwise `undefined`. Callers use this instead of reading
 * `currentValues[field.key]` directly, so rendering and change-comparison never drift apart.
 *
 * `field.path` walks a nested measurement body (`{"RGB": {"R": 0.5}}`) instead of the flat `key`
 * lookup - readonly fields only, a PUT body being always flat. A path that does not resolve
 * yields `undefined`, never a half-walked sub-object reaching `formatFieldValue()`.
 * @param {FieldDef} field
 * @param {Record<string, unknown>} currentValues
 * @returns {unknown}
 */
export function resolveFieldValue(field, currentValues) {
    let value;
    if (Array.isArray(field.path) && field.path.length > 0) {
        /** @type {unknown} */
        let cursor = currentValues;
        for (const step of field.path) {
            if (typeof cursor !== "object" || cursor === null) {
                cursor = undefined;
                break;
            }
            cursor = /** @type {Record<string, unknown>} */ (cursor)[step];
        }
        value = cursor;
    } else {
        value = currentValues[field.key];
    }
    return value === undefined ? field.defaultValue : value;
}

/**
 * @param {unknown} data
 * @returns {string[]} validation problems; empty means the shape is acceptable.
 */
export function validateDefinitions(data) {
    /** @type {string[]} */
    const problems = [];
    if (typeof data !== "object" || data === null) {
        return ["definitions.json is not a JSON object"];
    }
    const defs = /** @type {Record<string, unknown>} */ (data);

    if (typeof defs.schemaVersion !== "string" || !/^\d+\.\d+\.\d+$/.test(defs.schemaVersion)) {
        problems.push("schemaVersion is missing or not a semantic version string");
    } else {
        const major = Number(defs.schemaVersion.split(".")[0]);
        if (major !== SUPPORTED_SCHEMA_MAJOR) {
            problems.push(
                `schemaVersion major ${major} is not supported by this build (expected major ${SUPPORTED_SCHEMA_MAJOR})`,
            );
        }
    }
    if (typeof defs.device !== "object" || defs.device === null || typeof (/** @type {Record<string, unknown>} */ (defs.device).id) !== "string") {
        problems.push("device.id is missing");
    }
    if (typeof defs.landingSection !== "string") {
        problems.push("landingSection is missing");
    }
    // A missing/non-positive value would otherwise reach setTimeout() as undefined/0/negative,
    // firing an unthrottled tight polling loop instead of failing loudly here.
    if (typeof defs.defaultPollIntervalMs !== "number" || !(defs.defaultPollIntervalMs > 0)) {
        problems.push("defaultPollIntervalMs must be a positive number");
    }
    if (!Array.isArray(defs.sections) || defs.sections.length === 0) {
        problems.push("sections must be a non-empty array");
        return problems;
    }
    const sectionKeys = new Set();
    for (const [index, section] of defs.sections.entries()) {
        const where = `sections[${index}]`;
        if (typeof section !== "object" || section === null) {
            problems.push(`${where} is not an object`);
            continue;
        }
        const s = /** @type {Record<string, unknown>} */ (section);
        if (typeof s.key === "string") {
            sectionKeys.add(s.key);
        } else {
            problems.push(`${where}.key is missing`);
        }
        if (typeof s.label !== "string") {
            problems.push(`${where}.label is missing`);
        }
        if (typeof s.rest !== "object" || s.rest === null || typeof (/** @type {Record<string, unknown>} */ (s.rest).get) !== "string") {
            problems.push(`${where}.rest.get is missing`);
        }
        if (s.pollGroup !== "live" && s.pollGroup !== "settings" && s.pollGroup !== "none") {
            problems.push(`${where}.pollGroup must be "live", "settings", or "none"`);
        }
        if (s.pollIntervalMs !== undefined && (typeof s.pollIntervalMs !== "number" || !(s.pollIntervalMs > 0))) {
            problems.push(`${where}.pollIntervalMs must be a positive number when present`);
        }
        if (!Array.isArray(s.groups)) {
            problems.push(`${where}.groups must be an array`);
            continue;
        }
        for (const [gIndex, group] of s.groups.entries()) {
            const gWhere = `${where}.groups[${gIndex}]`;
            const g = /** @type {Record<string, unknown>} */ (group);
            if (typeof g.key !== "string" || typeof g.label !== "string") {
                problems.push(`${gWhere} is missing key/label`);
            }
            if (g.kind === "errcount") {
                problems.push(...validateErrcountGroup(g, gWhere));
                continue;
            }
            if (!Array.isArray(g.fields)) {
                problems.push(`${gWhere}.fields must be an array`);
                continue;
            }
            for (const [fIndex, field] of g.fields.entries()) {
                problems.push(...validateFieldHints(field, `${gWhere}.fields[${fIndex}]`));
            }
        }
    }
    if (defs.landingSection !== undefined && !sectionKeys.has(defs.landingSection)) {
        problems.push(`landingSection "${defs.landingSection}" does not match any section key`);
    }
    return problems;
}

/**
 * @param {unknown} value
 * @returns {boolean} true for a plain object whose every value is a string.
 */
function isStringMap(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value) && Object.values(value).every((v) => typeof v === "string");
}

/**
 * An errcount group's module list and, when present, its code-description block.
 * @param {Record<string, unknown>} g
 * @param {string} where
 * @returns {string[]}
 */
function validateErrcountGroup(g, where) {
    /** @type {string[]} */
    const problems = [];
    if (!Array.isArray(g.modules)) {
        problems.push(`${where}.modules must be an array for an errcount group`);
    }
    if (g.codes !== undefined) {
        const codes = /** @type {Record<string, unknown> | null} */ (typeof g.codes === "object" ? g.codes : null);
        if (codes === null || Array.isArray(codes) || !isStringMap(codes.E) || !isStringMap(codes.W)) {
            problems.push(`${where}.codes must map E and W to code descriptions`);
        }
    }
    return problems;
}

/**
 * The value-kind hints a string field carries: a byte bound and a shape, each only on a string.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @returns {string[]}
 */
function validateStringHints(f, where) {
    /** @type {string[]} */
    const problems = [];
    if (f.byteLength !== undefined && (typeof f.byteLength !== "boolean" || f.kind !== "string")) {
        problems.push(`${where}.byteLength must be a boolean on a string field when present`);
    }
    if (f.shape !== undefined && (typeof f.shape !== "string" || !STRING_SHAPES.has(f.shape) || f.kind !== "string")) {
        problems.push(`${where}.shape must be one of ${[...STRING_SHAPES].join(", ")} on a string field when present`);
    }
    return problems;
}

/**
 * Validates the display and value hints a field carries. This file's contract is to fail loudly
 * rather than in the browser, so a malformed hint has to surface here, naming where it sits.
 * @param {unknown} field
 * @param {string} where
 * @returns {string[]}
 */
function validateFieldHints(field, where) {
    /** @type {string[]} */
    const problems = [];
    if (typeof field !== "object" || field === null) {
        return problems; // the group-level shape checks above already own this case
    }
    const f = /** @type {Record<string, unknown>} */ (field);
    if (f.path !== undefined) {
        if (!Array.isArray(f.path) || f.path.length === 0 || !f.path.every((step) => typeof step === "string" && step !== "")) {
            problems.push(`${where}.path must be a non-empty array of non-empty strings when present`);
        } else if (f.kind !== "readonly") {
            // A PUT body is always flat, so a path on a writable field would render one value and
            // submit a different one.
            problems.push(`${where}.path is only valid on a readonly field, not kind "${String(f.kind)}"`);
        }
    }
    if (f.decimals !== undefined && (typeof f.decimals !== "number" || !Number.isInteger(f.decimals) || f.decimals < 0 || f.decimals > MAX_DECIMALS)) {
        problems.push(`${where}.decimals must be an integer from 0 to ${MAX_DECIMALS} when present`);
    }
    if (f.format !== undefined && (typeof f.format !== "string" || !FIELD_FORMATS.has(f.format) || f.kind !== "readonly")) {
        problems.push(`${where}.format must be one of ${[...FIELD_FORMATS].join(", ")} on a readonly field when present`);
    }
    if (f.codes !== undefined && !isStringMap(f.codes)) {
        problems.push(`${where}.codes must map each code to its description when present`);
    }
    if (f.alwaysExecuted !== undefined && typeof f.alwaysExecuted !== "boolean") {
        problems.push(`${where}.alwaysExecuted must be a boolean when present`);
    }
    problems.push(...validateStringHints(f, where));
    return problems;
}

/**
 * @param {string} path
 * @param {HTMLElement | null} [inlinedEl] a `<script type="application/json">` element already
 *   present in the page carrying this same data, or `null`/omitted if none. Never queried from
 *   `document` here - callers pass the element down, matching this module's usual convention.
 * @returns {Promise<SiteDefinitions>}
 */
export async function loadDefinitions(path, inlinedEl) {
    let data;
    if (inlinedEl) {
        // A real device build inlines definitions.json straight into index.html (cuts one
        // connection per page load); dev/preview mode never has this element, so the fetch path
        // below runs unchanged.
        try {
            data = JSON.parse(inlinedEl.textContent ?? "");
        } catch (error) {
            throw new Error("inlined definitions data was not valid JSON (a corrupted build)", { cause: error });
        }
    } else {
        const response = await fetchWithTimeout(path);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${path}: HTTP ${response.status}`);
        }
        try {
            data = await response.json();
        } catch (error) {
            // A genuine transmission error (truncated/corrupted response) - not this file's own
            // shape/version validation below, which only ever sees a syntactically valid JSON value.
            throw new Error(`${path} was not valid JSON (likely a corrupted or truncated transmission)`, { cause: error });
        }
    }
    const problems = validateDefinitions(data);
    if (problems.length > 0) {
        throw new Error(`${path} failed definitions validation:\n- ${problems.join("\n- ")}`);
    }
    return /** @type {SiteDefinitions} */ (data);
}
