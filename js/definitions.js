/**
 * Loads and strictly validates a device's definitions.json (WEBSITE_PLAN.md §4/§8). A shape/
 * version mismatch surfaces a visible error rather than silently rendering something broken or
 * skipping unknown fields (§4 "Definitions validation").
 *
 * @typedef {{value: string|number, label: string}} EnumOption
 * @typedef {{value: number, meaning: string}} SpecialValue
 * @typedef {{
 *   key: string, label: string, unit?: string, kind: "readonly"|"number"|"string"|"enum"|"toggle"|"composite",
 *   description?: string, min?: number, max?: number, minLength?: number, maxLength?: number,
 *   mask?: boolean, options?: EnumOption[], specialValues?: SpecialValue[],
 *   subFields?: FieldDef[], onLabel?: string, offLabel?: string,
 *   format?: "gmtimestruct", float?: boolean,
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

// A "number"-kind field's real server-side type is Python int by default; float?: true marks the
// few fields that are actually Python float. config_manager.py's coerce_numeric()/
// type_or_range_error() (SPECIFICATION.md Part A.8) accepts a JSON int for a float field
// unconditionally (a blanket accept - every int is exactly representable as a float), but a
// float field's own value is never subject to the int-only "no fractional part" check - so this
// flag's only remaining job (js/mock-server.js's coerceAndValidate()) is telling an int-typed
// field apart from a float-typed one so a fractional value is rejected only where it should be.

// errcount history shape matches src/print_log.py's get_log()/asy_webserver_service.py's
// _shape_errcount_entry() exactly: no per-entry timestamp exists anywhere in the real system, and
// "type" ("N"=no error/placeholder slot, "E"=error, "W"=warning) is never shown as text - only used
// to color "num" (js/templates.js's buildErrcountGroup(), html/style.css's
// .history-entry[data-err-type] rules). "num" is a raw errno the backend never attaches a
// human-meaning catalog to.

/** The only schema major version this build of the renderer understands. */
export const SUPPORTED_SCHEMA_MAJOR = 1;

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
    // Falls back to for any section that omits its own pollIntervalMs (js/render.js's
    // startPolling() call) - a missing/non-positive value would otherwise reach setTimeout() as
    // undefined/0/negative, firing an unthrottled tight polling loop instead of failing loudly here.
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
        if (typeof s.key !== "string") {
            problems.push(`${where}.key is missing`);
        } else {
            sectionKeys.add(s.key);
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
 * @returns {Promise<SiteDefinitions>}
 */
export async function loadDefinitions(path) {
    const response = await fetchWithTimeout(path);
    if (!response.ok) {
        throw new Error(`Failed to fetch ${path}: HTTP ${response.status}`);
    }
    let data;
    try {
        data = await response.json();
    } catch (error) {
        // A genuine transmission error (truncated/corrupted response) - not this file's own
        // shape/version validation below, which only ever sees a syntactically valid JSON value.
        throw new Error(`${path} was not valid JSON (likely a corrupted or truncated transmission)`, { cause: error });
    }
    const problems = validateDefinitions(data);
    if (problems.length > 0) {
        throw new Error(`${path} failed definitions validation:\n- ${problems.join("\n- ")}`);
    }
    return /** @type {SiteDefinitions} */ (data);
}
