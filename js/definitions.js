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
 *   subFields?: FieldDef[], onLabel?: string, offLabel?: string, format?: string,
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
 *     errcount: Record<string, {counter: number, history?: {TS: number, ErrType: string, ErrNum: number}[]}>,
 *   },
 * }} MockDeviceData
 */

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
    if (typeof defs.device !== "object" || defs.device === null || typeof (/** @type {any} */ (defs.device).id) !== "string") {
        problems.push("device.id is missing");
    }
    if (typeof defs.landingSection !== "string") {
        problems.push("landingSection is missing");
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
        if (typeof s.rest !== "object" || s.rest === null || typeof (/** @type {any} */ (s.rest).get) !== "string") {
            problems.push(`${where}.rest.get is missing`);
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
    const response = await fetch(path);
    if (!response.ok) {
        throw new Error(`Failed to fetch ${path}: HTTP ${response.status}`);
    }
    const data = await response.json();
    const problems = validateDefinitions(data);
    if (problems.length > 0) {
        throw new Error(`${path} failed definitions validation:\n- ${problems.join("\n- ")}`);
    }
    return /** @type {SiteDefinitions} */ (data);
}
