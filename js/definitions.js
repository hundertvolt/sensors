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
 *   landingSection: string, defaultPollIntervalMs: number, defaultDecimals?: number, sections: Section[],
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

// setTimeout's own ceiling; a larger delay fires at once.
const MAX_POLL_INTERVAL_MS = 2 ** 31 - 1;

// The enumerated values the generator emits (buildgen/web_tag.py's _FORMATS and _SHAPES, the catalog's tones).
const FIELD_KINDS = new Set(["readonly", "number", "string", "enum", "toggle", "composite"]);
const FIELD_FORMATS = new Set(["gmtimestruct", "epoch", "lasttaskend"]);
const STRING_SHAPES = new Set(["hostLabel", "countryCode", "hostName", "ipv4List"]);
const CODE_TONES = new Set(["good", "neutral", "warn"]);
const POLL_GROUPS = new Set(["live", "settings", "none"]);

// websiteVersion is build provenance only (SPECIFICATION.md Part L.7), distinct from
// schemaVersion's wire-format concern above. Nothing renders it - you always have exactly the
// build you fetched - so it is unvalidated too, and a bad value costs provenance, not rendering.

/**
 * @param {unknown} value
 * @returns {boolean} true for an integer the page can pass to Number#toFixed().
 */
function isDecimals(value) {
    return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= MAX_DECIMALS;
}

/**
 * @param {unknown} value
 * @returns {boolean} true for a delay setTimeout() waits out rather than firing at once.
 */
function isPollInterval(value) {
    return typeof value === "number" && value > 0 && value <= MAX_POLL_INTERVAL_MS;
}

/**
 * @param {unknown} value
 * @returns {boolean} true for a non-empty array of non-empty strings: a walk into a GET body.
 */
function isStepList(value) {
    return Array.isArray(value) && value.length > 0 && value.every((step) => typeof step === "string" && step !== "");
}

/**
 * @param {unknown} value
 * @returns {boolean} true for a plain object whose every value is a string.
 */
function isStringMap(value) {
    return isRecord(value) && Object.values(value).every((v) => typeof v === "string");
}

/**
 * Notes a key's first index, or a problem naming both indices when it repeats one.
 * @param {Map<string, number>} seen
 * @param {unknown} key
 * @param {number} index
 * @param {string} where the entry's own path
 * @param {string} listWhere the list's path
 * @param {string[]} problems
 */
function noteDuplicate(seen, key, index, where, listWhere, problems) {
    if (typeof key !== "string") {
        return;
    }
    const first = seen.get(key);
    if (first === undefined) {
        seen.set(key, index);
    } else {
        problems.push(`${where}.key "${key}" duplicates ${listWhere}[${first}]`);
    }
}

/**
 * The hints that describe a readonly value: its format, its code table with tones, its special values.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {string[]} problems
 */
function validateCodeHints(f, where, problems) {
    if (f.format !== undefined && (typeof f.format !== "string" || !FIELD_FORMATS.has(f.format) || f.kind !== "readonly")) {
        problems.push(`${where}.format must be one of ${[...FIELD_FORMATS].join(", ")} on a readonly field when present`);
    }
    if (f.codes !== undefined && !isStringMap(f.codes)) {
        problems.push(`${where}.codes must map each code to its description when present`);
    }
    if (f.codeTones !== undefined) {
        const codes = isRecord(f.codes) ? f.codes : {};
        const tones = isRecord(f.codeTones) ? Object.entries(f.codeTones) : null;
        if (tones === null || !tones.every(([code, tone]) => code in codes && typeof tone === "string" && CODE_TONES.has(tone))) {
            problems.push(`${where}.codeTones must map codes of this field to good, neutral or warn when present`);
        }
    }
    if (f.specialValues !== undefined && !(Array.isArray(f.specialValues) && f.specialValues.every((s) => isRecord(s) && "value" in s && typeof s.meaning === "string"))) {
        problems.push(`${where}.specialValues must be a list of {value, meaning} entries when present`);
    }
}

/**
 * An errcount group's module list and, when present, its code-description block.
 * @param {Record<string, unknown>} g
 * @param {string} where
 * @param {string[]} problems
 */
function validateErrcountGroup(g, where, problems) {
    if (Array.isArray(g.modules)) {
        for (const [index, module] of g.modules.entries()) {
            if (!isRecord(module) || typeof module.key !== "string" || typeof module.label !== "string") {
                problems.push(`${where}.modules[${index}] must carry a key and a label`);
            }
        }
    } else {
        problems.push(`${where}.modules must be an array for an errcount group`);
    }
    if (g.codes !== undefined) {
        const codes = isRecord(g.codes) ? g.codes : null;
        if (codes === null || !isStringMap(codes.E) || !isStringMap(codes.W)) {
            problems.push(`${where}.codes must map E and W to code descriptions`);
        }
    }
}

/**
 * One field: its key, label and kind, a composite's sub-fields, then its hints.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {unknown[]} siblingKeys every key of the field's own list, its own included
 * @param {string[]} problems
 */
function validateField(f, where, siblingKeys, problems) {
    if (typeof f.key !== "string") {
        problems.push(`${where}.key is missing`);
    }
    if (typeof f.label !== "string") {
        problems.push(`${where}.label is missing`);
    }
    if (typeof f.kind !== "string" || !FIELD_KINDS.has(f.kind)) {
        problems.push(`${where}.kind must be one of ${[...FIELD_KINDS].join(", ")}`);
    }
    if (f.kind === "composite") {
        if (Array.isArray(f.subFields)) {
            validateFields(f.subFields, `${where}.subFields`, problems);
        } else {
            problems.push(`${where}.subFields must be an array for a composite field`);
        }
    }
    validateHints(f, where, siblingKeys, problems);
}

/**
 * A list of fields (a group's, or a composite's sub-fields): each an object, each key once.
 * @param {unknown[]} fields
 * @param {string} where
 * @param {string[]} problems
 */
function validateFields(fields, where, problems) {
    /** @type {Map<string, number>} */
    const seen = new Map();
    const keys = fields.map((field) => (isRecord(field) ? field.key : undefined));
    for (const [index, field] of fields.entries()) {
        const fWhere = `${where}[${index}]`;
        if (!isRecord(field)) {
            problems.push(`${fWhere} is not an object`);
            continue;
        }
        noteDuplicate(seen, field.key, index, fWhere, where, problems);
        validateField(field, fWhere, keys, problems);
    }
}

/**
 * The flags a field carries: always executed, asks before it is sent, ignored while a sibling is set.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {unknown[]} siblingKeys
 * @param {string[]} problems
 */
function validateFlagHints(f, where, siblingKeys, problems) {
    if (f.alwaysExecuted !== undefined && typeof f.alwaysExecuted !== "boolean") {
        problems.push(`${where}.alwaysExecuted must be a boolean when present`);
    }
    if (f.confirm !== undefined && (typeof f.confirm !== "boolean" || (f.kind !== "enum" && f.kind !== "toggle"))) {
        problems.push(`${where}.confirm must be a boolean on an enum or toggle field when present`);
    }
    if (f.ignoredWhenSet !== undefined && (typeof f.ignoredWhenSet !== "string" || f.ignoredWhenSet === f.key || !siblingKeys.includes(f.ignoredWhenSet))) {
        problems.push(`${where}.ignoredWhenSet must name another field of its group when present`);
    }
}

/**
 * One group of a section: an errcount group, or a field group whose submit needs the section's rest.put.
 * @param {Record<string, unknown>} g
 * @param {string} where
 * @param {Record<string, unknown>} section
 * @param {string[]} problems
 */
function validateGroup(g, where, section, problems) {
    if (typeof g.key !== "string" || typeof g.label !== "string") {
        problems.push(`${where} is missing key/label`);
    }
    if (g.kind === "errcount") {
        validateErrcountGroup(g, where, problems);
        return;
    }
    if (!Array.isArray(g.fields)) {
        problems.push(`${where}.fields must be an array`);
        return;
    }
    if (g.submit === true && !(isRecord(section.rest) && typeof section.rest.put === "string")) {
        problems.push(`${where} is writable but its section has no rest.put`);
    }
    validateFields(g.fields, `${where}.fields`, problems);
}

/**
 * Validates the display and value hints a field carries. This file's contract is to fail loudly
 * rather than in the browser, so a malformed hint has to surface here, naming where it sits.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {unknown[]} siblingKeys
 * @param {string[]} problems
 */
function validateHints(f, where, siblingKeys, problems) {
    validatePathHints(f, where, problems);
    validateNumberHints(f, where, problems);
    validateCodeHints(f, where, problems);
    validateStringHints(f, where, problems);
    validateFlagHints(f, where, siblingKeys, problems);
}

/**
 * The hints that say how a number shows: its decimals, and the step the device rounds it to.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {string[]} problems
 */
function validateNumberHints(f, where, problems) {
    if (f.decimals !== undefined && !isDecimals(f.decimals)) {
        problems.push(`${where}.decimals must be an integer from 0 to ${MAX_DECIMALS} when present`);
    }
    if (f.resolution !== undefined && !(typeof f.resolution === "number" && Number.isFinite(f.resolution) && f.resolution > 0 && f.kind === "number")) {
        problems.push(`${where}.resolution must be a positive finite number on a number field when present`);
    }
}

/**
 * The walks that find a field's value: path into its own GET body, statusPath into GET /status's.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {string[]} problems
 */
function validatePathHints(f, where, problems) {
    if (f.path !== undefined) {
        if (!isStepList(f.path)) {
            problems.push(`${where}.path must be a non-empty array of non-empty strings when present`);
        } else if (f.kind !== "readonly") {
            // A PUT body is always flat, so a path on a writable field would render one value and
            // submit a different one.
            problems.push(`${where}.path is only valid on a readonly field, not kind "${String(f.kind)}"`);
        }
    }
    if (f.statusPath !== undefined && (!isStepList(f.statusPath) || (f.kind !== "readonly" && f.kind !== "number"))) {
        problems.push(`${where}.statusPath must be a non-empty array of non-empty strings on a readonly or number field when present`);
    }
}

/**
 * One section: its key, label, route and poll settings, then each group, each group key once.
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
    // js/render.js passes it to setTimeout(): 0, negative or above the ceiling would fire at once.
    if (s.pollIntervalMs !== undefined && !isPollInterval(s.pollIntervalMs)) {
        problems.push(`${where}.pollIntervalMs must be a positive number of at most ${MAX_POLL_INTERVAL_MS} ms`);
    }
    if (!Array.isArray(s.groups)) {
        problems.push(`${where}.groups must be an array`);
        return;
    }
    /** @type {Map<string, number>} */
    const seen = new Map();
    for (const [index, group] of s.groups.entries()) {
        const gWhere = `${where}.groups[${index}]`;
        if (!isRecord(group)) {
            problems.push(`${gWhere} is not an object`);
            continue;
        }
        noteDuplicate(seen, group.key, index, gWhere, `${where}.groups`, problems);
        validateGroup(group, gWhere, s, problems);
    }
}

/**
 * The value-kind hints a string field carries: a byte bound, a shape and a Clear button, each only on a string.
 * @param {Record<string, unknown>} f
 * @param {string} where
 * @param {string[]} problems
 */
function validateStringHints(f, where, problems) {
    if (f.byteLength !== undefined && (typeof f.byteLength !== "boolean" || f.kind !== "string")) {
        problems.push(`${where}.byteLength must be a boolean on a string field when present`);
    }
    if (f.shape !== undefined && (typeof f.shape !== "string" || !STRING_SHAPES.has(f.shape) || f.kind !== "string")) {
        problems.push(`${where}.shape must be one of ${[...STRING_SHAPES].join(", ")} on a string field when present`);
    }
    if (f.clearable !== undefined && (typeof f.clearable !== "boolean" || f.kind !== "string")) {
        problems.push(`${where}.clearable must be a boolean on a string field when present`);
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
    // A missing, non-positive or over-ceiling value would reach setTimeout() and fire an unthrottled
    // tight polling loop instead of failing loudly here.
    if (!isPollInterval(defs.defaultPollIntervalMs)) {
        problems.push(`defaultPollIntervalMs must be a positive number of at most ${MAX_POLL_INTERVAL_MS} ms`);
    }
    if (defs.defaultDecimals !== undefined && !isDecimals(defs.defaultDecimals)) {
        problems.push(`defaultDecimals must be an integer from 0 to ${MAX_DECIMALS} when present`);
    }
    if (!Array.isArray(defs.sections) || defs.sections.length === 0) {
        problems.push("sections must be a non-empty array");
        return problems;
    }
    /** @type {Map<string, number>} */
    const seen = new Map();
    for (const [index, section] of defs.sections.entries()) {
        const where = `sections[${index}]`;
        if (!isRecord(section)) {
            problems.push(`${where} is not an object`);
            continue;
        }
        noteDuplicate(seen, section.key, index, where, "sections", problems);
        validateSection(section, where, problems);
    }
    if (defs.landingSection !== undefined && !(typeof defs.landingSection === "string" && seen.has(defs.landingSection))) {
        problems.push(`landingSection "${String(defs.landingSection)}" does not match any section key`);
    }
    return problems;
}
