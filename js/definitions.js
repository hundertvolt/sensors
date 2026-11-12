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
 *   format?: "gmtimestruct"|"epoch"|"lasttaskend", float?: boolean, resolution?: number, dispatch?: boolean, alwaysExecuted?: boolean,
 *   path?: string[], statusPath?: string[], decimals?: number, byteLength?: boolean,
 *   shape?: "hostLabel"|"countryCode"|"hostName"|"ipv4List", clearable?: boolean, ignoredWhenSet?: string,
 *   codes?: Record<string, string>, codeTones?: Record<string, "good"|"neutral"|"warn">, confirm?: boolean,
 * }} FieldDef
 * @typedef {{key: string, label: string, fields: FieldDef[], submit?: boolean, submitLabel?: string}} FieldGroup
 * @typedef {{key: string, label: string, kind: "errcount", modules: {key: string, label: string}[]}} ErrcountGroup
 * @typedef {{E: Record<string, string>, W: Record<string, string>}} ErrcountCodes
 * @typedef {{
 *   key: string, label: string, description?: string,
 *   rest: {get: string, put?: string},
 *   pollGroup: "live"|"settings"|"none", pollIntervalMs?: number,
 *   groups: (FieldGroup|ErrcountGroup)[],
 * }} Section
 * @typedef {{
 *   schemaVersion: string, websiteVersion?: string, device: {id: string, displayName: string},
 *   landingSection: string, defaultPollIntervalMs: number, defaultDecimals?: number, errcountCodes?: ErrcountCodes,
 *   sections: Section[],
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

import { pollManager } from "./poll-manager.js";

// float?: true marks a "number"-kind field whose real server-side type is Python float, not the
// int default (SPECIFICATION.md Part A.8) - tells coerceAndValidate() when a fractional value is
// actually valid.

// errcount history shape matches asy_print_log.py/asy_webserver_service.py exactly: no per-entry
// timestamp exists; "type" ("N"/"E"/"W") only colors "num" (a raw errno), never shown as text.

// dispatch?: true and alwaysExecuted?: true mark the two never-"Unchanged" classes
// (SPECIFICATION.md Part H.5); neverUnchanged() below reads them - never a key list.

/** The only schema major version this build of the renderer understands. */
const SUPPORTED_SCHEMA_MAJOR = 1;

// Number#toFixed's own ceiling: a larger value would throw a RangeError in the card.
const MAX_DECIMALS = 100;

const POLL_GROUPS = new Set(["live", "settings", "none"]);

// websiteVersion is build provenance only (SPECIFICATION.md Part L.7), distinct from
// schemaVersion's wire-format concern above. Nothing renders it - you always have exactly the
// build you fetched - so it is unvalidated too, and a bad value costs provenance, not rendering.

/**
 * @param {unknown} value
 * @returns {boolean} true for a positive delay: 0, negative or NaN would fire setTimeout() at once.
 */
function isPollInterval(value) {
    return typeof value === "number" && value > 0;
}

/**
 * One group of a section: an errcount group, or a field group whose fields carry hints.
 * @param {Record<string, unknown>} g
 * @param {string} where
 * @param {string[]} problems
 */
function validateGroup(g, where, problems) {
    if (typeof g.key !== "string" || typeof g.label !== "string") {
        problems.push(`${where} is missing key/label`);
    }
    if (g.kind === "errcount") {
        if (!Array.isArray(g.modules)) {
            problems.push(`${where}.modules must be an array for an errcount group`);
        }
        return;
    }
    if (!Array.isArray(g.fields)) {
        problems.push(`${where}.fields must be an array`);
        return;
    }
    for (const [index, field] of g.fields.entries()) {
        if (isRecord(field)) {
            validateHints(field, `${where}.fields[${index}]`, problems);
        }
    }
}

/**
 * Validates the two display hints a nested, precision-declared readonly field carries: this file's
 * contract is to fail loudly rather than in the browser, so a malformed one surfaces here.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {string[]} problems
 */
function validateHints(f, where, problems) {
    if (f.path !== undefined) {
        if (!(Array.isArray(f.path) && f.path.length > 0 && f.path.every((step) => typeof step === "string" && step !== ""))) {
            problems.push(`${where}.path must be a non-empty array of non-empty strings when present`);
        } else if (f.kind !== "readonly") {
            // A PUT body is always flat, so a path on a writable field would render one value and
            // submit a different one.
            problems.push(`${where}.path is only valid on a readonly field, not kind "${String(f.kind)}"`);
        }
    }
    if (f.decimals !== undefined && !(typeof f.decimals === "number" && Number.isInteger(f.decimals) && f.decimals >= 0 && f.decimals <= MAX_DECIMALS)) {
        problems.push(`${where}.decimals must be an integer from 0 to ${MAX_DECIMALS} when present`);
    }
}

/**
 * One section: its key, label, route and poll settings, then each group.
 * @param {Record<string, unknown>} s
 * @param {string} where
 * @param {string[]} problems
 */
function validateSection(s, where, problems) {
    if (typeof s.key !== "string") {
        problems.push(`${where}.key is missing`);
    }
    if (typeof s.label !== "string") {
        problems.push(`${where}.label is missing`);
    }
    if (!isRecord(s.rest) || typeof s.rest.get !== "string") {
        problems.push(`${where}.rest.get is missing`);
    }
    if (typeof s.pollGroup !== "string" || !POLL_GROUPS.has(s.pollGroup)) {
        problems.push(`${where}.pollGroup must be "live", "settings", or "none"`);
    }
    if (s.pollIntervalMs !== undefined && !isPollInterval(s.pollIntervalMs)) {
        problems.push(`${where}.pollIntervalMs must be a positive number when present`);
    }
    if (!Array.isArray(s.groups)) {
        problems.push(`${where}.groups must be an array`);
        return;
    }
    for (const [index, group] of s.groups.entries()) {
        validateGroup(/** @type {Record<string, unknown>} */ (group), `${where}.groups[${index}]`, problems);
    }
}

/**
 * The one plain-object check of every js/ module: any object but null and an array, an `Object.create(null)`
 * object and a class instance included.
 * @param {unknown} value
 * @returns {value is Record<string, unknown>}
 */
export function isRecord(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
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
        const response = await pollManager.request(path);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${path}: HTTP ${response.status}`);
        }
        data = response.body;
    }
    const problems = validateDefinitions(data);
    if (problems.length > 0) {
        throw new Error(`${path} failed definitions validation:\n- ${problems.join("\n- ")}`);
    }
    return /** @type {SiteDefinitions} */ (data);
}

/**
 * True for the two classes the server never answers "Unchanged" (SPECIFICATION.md Part H.5).
 * @param {FieldDef} field
 * @returns {boolean}
 */
export function neverUnchanged(field) {
    return field.dispatch === true || field.alwaysExecuted === true;
}

/**
 * A field's current value: the `path` walk for a nested body, else `currentValues[field.key]`;
 * `undefined` when GET reported none. Callers use this instead of reading `currentValues[field.key]`
 * directly, so rendering and change-comparison never drift apart.
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
    return value;
}

/**
 * Every rejection names where it sits; the shape checks below run per section, group and field.
 * @param {unknown} data
 * @returns {string[]} validation problems; empty means the shape is acceptable.
 */
export function validateDefinitions(data) {
    /** @type {string[]} */
    const problems = [];
    if (!isRecord(data)) {
        return ["definitions.json is not a JSON object"];
    }
    const defs = data;
    if (typeof defs.schemaVersion !== "string" || !/^\d+\.\d+\.\d+$/.test(defs.schemaVersion)) {
        problems.push("schemaVersion is missing or not a semantic version string");
    } else {
        const major = Number(defs.schemaVersion.split(".")[0]);
        if (major !== SUPPORTED_SCHEMA_MAJOR) {
            problems.push(`schemaVersion major ${major} is not supported by this build (expected major ${SUPPORTED_SCHEMA_MAJOR})`);
        }
    }
    if (!isRecord(defs.device) || typeof defs.device.id !== "string") {
        problems.push("device.id is missing");
    }
    if (typeof defs.landingSection !== "string") {
        problems.push("landingSection is missing");
    }
    // A missing or non-positive value would reach setTimeout() and fire an unthrottled tight
    // polling loop instead of failing loudly here.
    if (!isPollInterval(defs.defaultPollIntervalMs)) {
        problems.push("defaultPollIntervalMs must be a positive number");
    }
    if (!Array.isArray(defs.sections) || defs.sections.length === 0) {
        problems.push("sections must be a non-empty array");
        return problems;
    }
    /** @type {Set<unknown>} */
    const sectionKeys = new Set();
    for (const [index, section] of defs.sections.entries()) {
        const where = `sections[${index}]`;
        if (!isRecord(section)) {
            problems.push(`${where} is not an object`);
            continue;
        }
        sectionKeys.add(section.key);
        validateSection(section, where, problems);
    }
    if (defs.landingSection !== undefined && !sectionKeys.has(defs.landingSection)) {
        problems.push(`landingSection "${String(defs.landingSection)}" does not match any section key`);
    }
    return problems;
}
