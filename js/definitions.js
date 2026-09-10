/**
 * Loads and strictly validates a device's definitions.json (SPECIFICATION.md Part H.5). A shape/
 * version mismatch surfaces a visible error rather than silently rendering something broken or
 * skipping unknown fields (Part H.4's "Definitions validation").
 *
 * @typedef {{value: string|number, label: string}} EnumOption
 * @typedef {{value: number, meaning: string}} SpecialValue
 * @typedef {{
 *   key: string, label: string, unit?: string, kind: "readonly"|"number"|"string"|"enum"|"toggle"|"composite",
 *   description?: string, min?: number, max?: number, minLength?: number, maxLength?: number,
 *   mask?: boolean, options?: EnumOption[], specialValues?: SpecialValue[],
 *   subFields?: FieldDef[], onLabel?: string, offLabel?: string,
 *   format?: "gmtimestruct", float?: boolean, dispatch?: boolean, defaultValue?: unknown,
 * }} FieldDef
 * @typedef {{key: string, label: string, fields: FieldDef[], submit?: boolean, submitLabel?: string}} FieldGroup
 * @typedef {{key: string, label: string, kind: "errcount", modules: {key: string, label: string}[]}} ErrcountGroup
 * @typedef {{
 *   key: string, label: string, description?: string,
 *   rest: {get: string, put?: string},
 *   pollGroup: "live"|"settings"|"none", pollIntervalMs?: number,
 *   groups: (FieldGroup|ErrcountGroup)[],
 * }} Section
 * @typedef {{
 *   schemaVersion: string, device: {id: string, displayName: string},
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
 */

import { fetchWithTimeout } from "./poll-manager.js";

// float?: true marks a "number"-kind field whose real server-side type is Python float, not the
// int default (SPECIFICATION.md Part A.8) - tells coerceAndValidate() when a fractional value is
// actually valid.

// errcount history shape matches print_log.py/asy_webserver_service.py exactly: no per-entry
// timestamp exists; "type" ("N"/"E"/"W") only colors "num" (a raw errno), never shown as text.

// dispatch?: true marks a toggle/enum field the backend always re-runs fresh, never compares
// against a stored value (SPECIFICATION.md Part H.6's dispatch-only list) - collectGroupBody()
// must always resubmit it, unlike an ordinary sparse-omitted-when-unchanged persisted field.

// defaultValue is a field's safe synthetic baseline for when GET never reports a real value (a
// command with no persisted state, e.g. SCD30's ContMeas) - see resolveFieldValue() below.

/** The only schema major version this build of the renderer understands. */
export const SUPPORTED_SCHEMA_MAJOR = 1;

/**
 * A field's effective current value: the real value from `currentValues` when GET reported one,
 * otherwise `field.defaultValue`, otherwise `undefined`. Callers use this instead of reading
 * `currentValues[field.key]` directly, so rendering and change-comparison never drift apart.
 * @param {FieldDef} field
 * @param {Record<string, unknown>} currentValues
 * @returns {unknown}
 */
export function resolveFieldValue(field, currentValues) {
    const value = currentValues[field.key];
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
                if (!Array.isArray(g.modules)) {
                    problems.push(`${gWhere}.modules must be an array for an errcount group`);
                }
                continue;
            }
            if (!Array.isArray(g.fields)) {
                problems.push(`${gWhere}.fields must be an array`);
            }
        }
    }
    if (defs.landingSection !== undefined && !sectionKeys.has(defs.landingSection)) {
        problems.push(`landingSection "${defs.landingSection}" does not match any section key`);
    }
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
