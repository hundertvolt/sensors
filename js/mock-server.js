/**
 * Prototype-only fake backend: intercepts window.fetch() for the routes the definitions declare and answers
 * exactly as the real server does, from data composed per device (SPECIFICATION.md Part H.4). Never staged;
 * everything outside this file targets the real API.
 */

import { FAILED, INVALID, UNCHANGED, VALID, isUnavailable } from "./api-contract.js";
import { isRecord, neverUnchanged } from "./definitions.js";

// src/asy_base_classes.py's COUNTER_CAP: 2**30 - 1, no counter exceeds it.
const COUNTER_CAP = 2 ** 30 - 1;
// src/asy_api_response.py's _STANDARD_CODES (SPECIFICATION.md C.5.3).
/** @type {Record<number, string>} */
const STANDARD_CODES = { 0: "Command executed", 1: "Invalid JSON request", 400: "Bad request", 404: "Not found", 405: "Method not allowed", 413: "Payload too large", 500: "Internal server error" };
const LED_BUSY_DESCR = "LED busy - retry later"; // src/asy_webserver_service.py's _LED_BUSY_DESCR
const LED_DURATION_MEMBER = "T"; // the seconds member of src/asy_webserver_service.py's _LIGHT_CMD_FIELDS
const DNS_LABEL_MAX = 63; // matches src/asy_dns_client.py's own DNS_LABEL_MAX
const IPV4_OCTET_MAX = 255;
const DNS_FALLBACK_MAX = 3; // src/asy_ntp_client.py's _DNS_FALLBACK_MAX: the most servers _dns_fallback_ok() accepts

/**
 * One rule per string shape, the same as src/'s host_label_ok(), _country_ok(), _ntp_host_ok() and
 * _dns_fallback_ok(): a host name is an IPv4 literal or dot-separated labels of at most 63 characters.
 * @type {Record<string, (value: string) => boolean>}
 */
const STRING_SHAPE_OK = {
    hostLabel: isHostLabel,
    countryCode: (value) => /^[A-Z]{2}$/.test(value),
    hostName: (value) => isIpv4Literal(value) || value.split(".").every((label) => label.length <= DNS_LABEL_MAX && isHostLabel(label)),
    ipv4List: (value) => {
        const servers = value.split(",");
        return value === "" || (servers.length <= DNS_FALLBACK_MAX && servers.every(isIpv4Literal));
    },
};

/**
 * The state a PUT reaches beyond its own stored config: the status data a statusPath writes into, when the
 * last LED command that ran ends (Date.now() ms), and whether this request's LED command was refused as busy.
 * @typedef {{status: Record<string, unknown>, busyUntil: number, busyRefused: boolean}} PutContext
 */

/**
 * One-shot failure for the next intercepted request, consumed once; `delayMs` delays every answer by a fixed time.
 * @typedef {"network" | number | "malformed-body" | "torn-json" | "empty-body" | "group-failure"} MockFailure
 * @typedef {{nextFailure?: MockFailure | undefined, delayMs?: number}} MockFetchControls
 */

/**
 * An RFC 1123 host label: letters, digits and "-", not "-" at either end; the caller bounds its length.
 * @param {string} value
 * @returns {boolean}
 */
function isHostLabel(value) {
    return /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(value);
}

/**
 * A dotted-quad IPv4 literal as src/asy_dns_client.py's ipv4_to_int() reads one: four octets of
 * ASCII digits, each at most 255 (leading zeros allowed).
 * @param {string} value
 * @returns {boolean}
 */
function isIpv4Literal(value) {
    const octets = value.split(".");
    return octets.length === 4 && octets.every((octet) => /^[0-9]+$/.test(octet) && Number(octet) <= IPV4_OCTET_MAX);
}

/**
 * Whether a request carries a JSON body as Microdot reads one: Request.json parses only under the exact type
 * application/json before any ";" (ext/microdot.py), so the server's _body_as_dict() refuses every other request.
 * @param {RequestInit | undefined} init
 * @returns {boolean}
 */
function isJsonRequest(init) {
    const contentType = new Headers(init?.headers).get("Content-Type");
    return contentType !== null && contentType.split(";")[0] === "application/json";
}

/**
 * One sparse PUT field's word: an action (dispatch) is dispatched and never stored; an always-executed field
 * answers Valid and is stored only when the composed data carries its key, so GET reads back what the chip
 * reports (AmbPres, ForceCalRef) and never a command it cannot report (ContMeas); any other is stored if changed.
 * @param {import("./definitions.js").FieldDef | undefined} field
 * @param {unknown} rawValue
 * @param {Record<string, unknown>} storedConfig
 * @param {PutContext} context
 * @returns {string}
 */
function applyField(field, rawValue, storedConfig, context) {
    if (field === undefined) {
        return INVALID; // a key the definitions do not list here, as the server answers it
    }
    if (field.dispatch === true) {
        return dispatchField(field, rawValue, context);
    }
    if (field.kind === "composite") {
        const members = /** @type {Record<string, unknown> | undefined} */ (rawValue);
        return (field.subFields ?? []).every((subField) => coerceAndValidate(subField, members?.[subField.key]).valid) ? VALID : INVALID;
    }
    const { valid, value } = coerceAndValidate(field, rawValue);
    if (!valid) {
        return INVALID;
    }
    if (neverUnchanged(field)) {
        if (field.key in storedConfig) {
            storedConfig[field.key] = value;
        }
        return VALID;
    }
    return storeIfChanged(field, value, storedConfig);
}

/**
 * @param {Record<string, unknown>} body
 * @param {Map<string, import("./definitions.js").FieldDef>} fieldDefs
 * @param {Record<string, unknown>} storedConfig
 * @param {PutContext} context
 * @returns {Record<string, string>}
 */
function applySparsePut(body, fieldDefs, storedConfig, context) {
    /** @type {Record<string, string>} */
    const results = {};
    for (const [key, rawValue] of Object.entries(body)) {
        results[key] = applyField(fieldDefs.get(key), rawValue, storedConfig, context);
    }
    return results;
}

/**
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @returns {{valid: boolean, value: unknown}}
 */
function coerceAndValidate(field, rawValue) {
    if (field.kind === "number") {
        // No Number(rawValue) coercion: the real backend does a strict type() check before ever
        // looking at magnitude, so a JSON string (even "42") is rejected outright, never parsed.
        if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
            return { valid: false, value: rawValue };
        }
        // Mirrors the real int<->float policy (SPECIFICATION.md Part A.8): a field not marked
        // field.float is int-typed and rejects any fractional value outright, same as out-of-range;
        // a float-typed field accepts any finite value, whole or fractional.
        if (field.float !== true && !Number.isInteger(rawValue)) {
            return { valid: false, value: rawValue };
        }
        const value = rawValue;
        const specialValues = field.specialValues ?? [];
        if (specialValues.some((special) => special.value === value)) {
            return { valid: true, value };
        }
        const min = field.min ?? -Infinity;
        const max = field.max ?? Infinity;
        return { valid: value >= min && value <= max, value };
    }
    if (field.kind === "string") {
        // No String(rawValue) coercion, for the same reason as the number branch above: the real
        // backend's type_or_range_error() rejects a non-str JSON value outright (e.g. a JSON
        // number sent to a string field), it never stringifies it first.
        if (typeof rawValue !== "string") {
            return { valid: false, value: rawValue };
        }
        return { valid: stringValueOk(field, rawValue), value: rawValue };
    }
    if (field.kind === "enum") {
        // Compare as-sent, not string-coerced: an enum's real value can be numeric (e.g. BMP3XX's
        // PresOvers) and then needs the same int-only strictness as an ordinary int field; a string
        // option (SystemCmd's words) matches only as a whole.
        if (typeof rawValue === "number" && !Number.isInteger(rawValue)) {
            return { valid: false, value: rawValue };
        }
        const options = field.options ?? [];
        return { valid: options.some((option) => option.value === rawValue), value: rawValue };
    }
    if (field.kind === "toggle") {
        return { valid: typeof rawValue === "boolean", value: Boolean(rawValue) };
    }
    return { valid: true, value: rawValue };
}

/**
 * One errcount group's share of the composed data (see composeMockData()): each module takes its driver's
 * sample; a module with no sample throws, as a group does, rather than composing a healthy zero.
 * @param {import("./definitions.js").MockDeviceData} data
 * @param {import("./definitions.js").MockSamples} samples
 * @param {import("./definitions.js").ErrcountGroup} group
 * @param {string} where
 */
function composeErrcountGroup(data, samples, group, where) {
    for (const module of group.modules) {
        const name = sampleNameFor(Object.keys(samples.errcount), module.key);
        const sample = name === undefined ? undefined : samples.errcount[name];
        if (sample === undefined) {
            throw new Error(`mock samples: no sample for module "${where}/${module.key}"`);
        }
        data.status.errcount[module.key] = structuredClone(sample);
    }
}

/**
 * One field group's share of the composed data (see composeMockData()). A dispatch field is a
 * command, never part of a GET body, so it is never copied.
 * @param {import("./definitions.js").MockDeviceData} data
 * @param {import("./definitions.js").MockSamples} samples
 * @param {string} sectionKey
 * @param {import("./definitions.js").FieldGroup} group
 * @param {string} where
 */
function composeGroup(data, samples, sectionKey, group, where) {
    const fields = group.fields.filter((field) => field.dispatch !== true);
    if (sectionKey === "measurements" || sectionKey === "sensors") {
        const pool = sectionKey === "measurements" ? samples.measurements : samples.sensorsConfig;
        const name = sampleNameFor(Object.keys(pool), group.key);
        const source = name === undefined ? undefined : pool[name];
        if (source === undefined) {
            throw new Error(`mock samples: no sample for group "${where}"`);
        }
        const dest = sectionKey === "measurements" ? data.measurements : data.sensorsConfig;
        dest[group.key] = {};
        copyNamedFields(source, fields, /** @type {Record<string, unknown>} */ (dest[group.key]));
        return;
    }
    if (sectionKey === "networking" || sectionKey === "system" || sectionKey === "notification") {
        copyNamedFields(samples[`${sectionKey}Config`], fields, data[`${sectionKey}Config`]);
        return;
    }
    if (fields.length === 0) {
        return; // a command-only group, e.g. the error reset: no GET data of its own
    }
    if (group.key === "sensors") {
        data.status.sensors = composeMaintenance(samples.status.sensors, fields, where);
        return;
    }
    const statusKey = /** @type {"networking" | "system" | "notification"} */ (group.key);
    const source = samples.status[statusKey];
    if (source === undefined) {
        throw new Error(`mock samples: no sample for group "${where}"`);
    }
    copyNamedFields(source, fields, data.status[statusKey]);
}

/**
 * The maintenance group's entries, read by each field's `path` (`[<module name>, <leaf>]`) as the
 * server keys them, each filled from the sample of the driver its module name takes.
 * @param {Record<string, Record<string, unknown>>} samples
 * @param {import("./definitions.js").FieldDef[]} fields
 * @param {string} where
 * @returns {Record<string, Record<string, unknown>>}
 */
function composeMaintenance(samples, fields, where) {
    /** @type {Record<string, Record<string, unknown>>} */
    const byModule = {};
    for (const field of fields) {
        const [moduleName, leaf] = field.path ?? [];
        const name = moduleName === undefined ? undefined : sampleNameFor(Object.keys(samples), moduleName);
        const source = name === undefined ? undefined : samples[name];
        if (moduleName === undefined || leaf === undefined || source === undefined) {
            throw new Error(`mock samples: no sample for "${where}/${field.key}"`);
        }
        byModule[moduleName] ??= {};
        if (leaf in source) {
            byModule[moduleName][leaf] = structuredClone(source[leaf]);
        }
    }
    return byModule;
}

/**
 * Copies from `source` only what `fields` name; a `path` field copies its top-level parent.
 * @param {Record<string, unknown>} source
 * @param {import("./definitions.js").FieldDef[]} fields
 * @param {Record<string, unknown>} dest
 */
function copyNamedFields(source, fields, dest) {
    for (const field of fields) {
        const top = field.path?.[0] ?? field.key;
        if (top in source) {
            dest[top] = structuredClone(source[top]);
        }
    }
}

/**
 * The LED command (SPECIFICATION.md Part A.8): Invalid for a non-object, a member missing or not in its subFields,
 * or one its sub-field refuses; Failed while the duration of the last command that ran is not over (the device
 * refuses a command while a signal runs), else Valid, starting that duration.
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @param {PutContext} context
 * @returns {string}
 */
function dispatchComposite(field, rawValue, context) {
    const subFields = field.subFields ?? [];
    if (!isRecord(rawValue) || Object.keys(rawValue).length !== subFields.length) {
        return INVALID;
    }
    if (!subFields.every((subField) => Object.hasOwn(rawValue, subField.key) && coerceAndValidate(subField, rawValue[subField.key]).valid)) {
        return INVALID;
    }
    if (Date.now() < context.busyUntil) {
        context.busyRefused = true;
        return FAILED;
    }
    const seconds = rawValue[LED_DURATION_MEMBER];
    context.busyUntil = Date.now() + (typeof seconds === "number" ? seconds * 1000 : 0);
    return VALID;
}

/**
 * One action field, never stored: an enum is Valid for exactly one of its options, a toggle for a boolean, a number
 * in its bounds (then written where its statusPath points); a composite is dispatchComposite()'s.
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @param {PutContext} context
 * @returns {string}
 */
function dispatchField(field, rawValue, context) {
    if (field.kind === "composite") {
        return dispatchComposite(field, rawValue, context);
    }
    const { valid, value } = coerceAndValidate(field, rawValue);
    if (!valid) {
        return INVALID;
    }
    if (field.statusPath !== undefined) {
        writeAtPath(context.status, field.statusPath, value);
    }
    return VALID;
}

/**
 * Every word of a PUT result, nested sensor maps included, turned into "Failed": a failed group's answer.
 * @param {Record<string, unknown>} results
 * @returns {Record<string, unknown>}
 */
function failEvery(results) {
    return Object.fromEntries(Object.entries(results).map(([key, word]) => [key, isRecord(word) ? failEvery(word) : FAILED]));
}

/**
 * Every field of a section's field groups (an errcount group has none).
 * @param {import("./definitions.js").Section} section
 * @returns {import("./definitions.js").FieldDef[]}
 */
function fieldsOf(section) {
    return section.groups.flatMap((group) => ("fields" in group ? group.fields : []));
}

/**
 * A flat section's PUT field map. A readonly field is left out: the server's settings groups list
 * writable fields only, so a readonly key answers "Invalid" like any key no group lists.
 * @param {import("./definitions.js").Section} section
 * @returns {Map<string, import("./definitions.js").FieldDef>}
 */
function flatFieldDefsFor(section) {
    return new Map(fieldsOf(section).filter((field) => field.kind !== "readonly").map((field) => [field.key, field]));
}

/**
 * The answer a pending injected failure gives in place of the real one, consuming it; undefined when none is
 * pending or it is a group failure, which handlePut() consumes. A network failure throws, as fetch() does.
 * @param {MockFetchControls | undefined} controls
 * @returns {Response | undefined}
 */
function injectedFailure(controls) {
    const failure = controls?.nextFailure;
    if (controls === undefined || failure === undefined || failure === "group-failure") {
        return undefined;
    }
    controls.nextFailure = undefined;
    if (failure === "network") {
        throw new TypeError("Failed to fetch (simulated network failure)");
    }
    if (failure === "malformed-body") {
        // Matches the backend's own make_response(1) (SPECIFICATION.md C.5.3): a body Request.json
        // cannot parse, or that parses to something other than an object, is a clean
        // HTTP 200 with res:"ERR" rather than a shaped HTTP error status.
        return jsonResponse(makeResponse(1));
    }
    if (failure === "torn-json") {
        // A connection dropped/corrupted mid-response: HTTP succeeds but the body isn't
        // valid JSON - a genuine transmission error, not a request the backend rejected.
        return new Response("{\"res\": \"OK\", \"code\": 0, tru", { status: 200 });
    }
    if (failure === "empty-body") {
        return new Response("", { status: 200 });
    }
    return jsonResponse(makeResponse(failure), failure);
}

/**
 * Jitters each sensor's measurement body in place (jitterInPlace()).
 * @param {Record<string, Record<string, unknown>>} bySensor
 */
function jitterEachSensorGroup(bySensor) {
    for (const sensorGroup of Object.values(bySensor)) {
        jitterInPlace(sensorGroup);
    }
}

/**
 * Nudges every numeric measurement leaf by a small random jitter so polled values move; a time key
 * (ending TS or Uptime) never jitters.
 * @param {Record<string, unknown>} group
 */
function jitterInPlace(group) {
    for (const [key, value] of Object.entries(group)) {
        if (isRecord(value)) {
            jitterInPlace(value); // a nested body (the ISL29125's RGB/HSB) moves too: static leaves read as a broken renderer
            continue;
        }
        if (typeof value !== "number" || key.endsWith("TS") || key.endsWith("Uptime")) {
            continue;
        }
        // Spread and rounding were sized for readings of order hundreds (CO2 ~600). On the
        // ISL29125's normalised 0-1 leaves a 0.05 floor is +-178%, taking them NEGATIVE, and
        // two decimals quantise to 0.00. Below 1 both scale with the value; above it, nothing.
        const magnitude = Math.abs(value);
        const spread = magnitude >= 1 ? Math.max(magnitude * 0.01, 0.05) : magnitude * 0.05;
        const factor = magnitude >= 1 ? 100 : 10000;
        group[key] = Math.round((value + (Math.random() * 2 - 1) * spread) * factor) / factor;
    }
}

/**
 * @param {unknown} data
 * @param {number} [status]
 * @returns {Response}
 */
function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

/**
 * The envelope src/asy_api_response.py's make_response() builds.
 * @param {number} code
 * @param {{descr?: string, result?: Record<string, unknown>}} [parts]
 * @returns {{res: string, code: number, descr: string, result: Record<string, unknown>}}
 */
function makeResponse(code, { descr, result } = {}) {
    return { res: code === 0 ? "OK" : "ERR", code, descr: descr ?? STANDARD_CODES[code] ?? "Unknown error", result: result ?? {} };
}

/**
 * A PUT body as the server reads one (_body_as_dict()): the parsed object, else undefined for a body
 * that does not parse or parses to anything but an object.
 * @param {string} rawBodyText
 * @returns {Record<string, unknown> | undefined}
 */
function parseBody(rawBodyText) {
    try {
        const parsed = JSON.parse(rawBodyText);
        return isRecord(parsed) ? parsed : undefined;
    } catch {
        return undefined;
    }
}

/**
 * The section each route serves, per method: GET from every section's `rest.get`, PUT from its `rest.put`.
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @returns {{get: Map<string, import("./definitions.js").Section>, put: Map<string, import("./definitions.js").Section>}}
 */
function routesOf(defs) {
    const routes = { get: new Map(), put: new Map() };
    for (const section of defs.sections) {
        routes.get.set(section.rest.get, section);
        if (section.rest.put !== undefined) {
            routes.put.set(section.rest.put, section);
        }
    }
    return routes;
}

/**
 * The sample name a group or module key takes: the longest name it equals or extends with `_`
 * (`SCD30_primary` takes `SCD30`; `CFGMGR_SCD30_primary` takes `CFGMGR_SCD30`, the longer name).
 * @param {string[]} names
 * @param {string} key
 * @returns {string | undefined}
 */
function sampleNameFor(names, key) {
    const matching = names.filter((name) => key === name || key.startsWith(`${name}_`));
    return matching.sort((a, b) => b.length - a.length)[0];
}

/**
 * Each /sensors group's PUT field map, writable fields only as flatFieldDefsFor()'s.
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @returns {Map<string, Map<string, import("./definitions.js").FieldDef>>}
 */
function sensorFieldDefsFor(defs) {
    const section = defs.sections.find((entry) => entry.key === "sensors");
    /** @type {Map<string, Map<string, import("./definitions.js").FieldDef>>} */
    const bySensor = new Map();
    for (const group of section?.groups ?? []) {
        if (!("fields" in group)) {
            continue; // an ErrcountGroup, not a FieldGroup
        }
        const writable = group.fields.filter((field) => field.kind !== "readonly");
        bySensor.set(group.key, new Map(writable.map((field) => [field.key, field])));
    }
    return bySensor;
}

/**
 * Adds one to `record[key]` while it is below COUNTER_CAP, as the server's counters saturate.
 * @param {Record<string, unknown>} record
 * @param {string} key
 */
function stepCounter(record, key) {
    const value = record[key];
    if (typeof value === "number" && value < COUNTER_CAP) {
        record[key] = value + 1;
    }
}

/**
 * A validated value against the stored one: Unchanged when equal, else stored and Valid. With a resolution both
 * are compared in its steps and the value is stored rounded to one, as the device reads it back.
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} value
 * @param {Record<string, unknown>} storedConfig
 * @returns {string}
 */
function storeIfChanged(field, value, storedConfig) {
    const { resolution } = field;
    const stored = storedConfig[field.key];
    if (resolution !== undefined && typeof value === "number") {
        const step = Math.round(value / resolution);
        if (typeof stored === "number" && Math.round(stored / resolution) === step) {
            return UNCHANGED;
        }
        // toPrecision drops the product's binary noise (1235 * 0.01 = 12.350000000000001).
        storedConfig[field.key] = Number((step * resolution).toPrecision(15));
        return VALID;
    }
    if (stored === value) {
        return UNCHANGED;
    }
    storedConfig[field.key] = value;
    return VALID;
}

/**
 * A string value the server accepts: a schema special, else within the character bounds, the
 * UTF-8 byte bound (`byteLength`) and the field's shape.
 * @param {import("./definitions.js").FieldDef} field
 * @param {string} value
 * @returns {boolean}
 */
function stringValueOk(field, value) {
    if ((field.specialValues ?? []).some((special) => special.value === value)) {
        return true;
    }
    const minLength = field.minLength ?? 0;
    const maxLength = field.maxLength ?? Infinity;
    if (value.length < minLength || value.length > maxLength) {
        return false;
    }
    if (field.byteLength && new TextEncoder().encode(value).length > maxLength) {
        return false;
    }
    if (field.shape === undefined) {
        return true;
    }
    const shapeOk = STRING_SHAPE_OK[field.shape];
    return shapeOk !== undefined && shapeOk(value); // a shape this mock does not know refuses, never passes
}

/**
 * Writes `value` at `path` (a field's statusPath) under `root`. A path through no object is a definitions
 * fault, thrown so the request fails visibly rather than storing the value nowhere.
 * @param {Record<string, unknown>} root
 * @param {string[]} path
 * @param {unknown} value
 */
function writeAtPath(root, path, value) {
    let cursor = root;
    for (const step of path.slice(0, -1)) {
        const next = cursor[step];
        if (!isRecord(next)) {
            throw new Error(`mock: statusPath ${path.join(".")} runs through no object`);
        }
        cursor = next;
    }
    const leaf = path.at(-1);
    if (leaf === undefined) {
        throw new Error("mock: an empty statusPath");
    }
    cursor[leaf] = value;
}

/**
 * Builds one device's mock data: each group and errcount module takes the sample of the driver whose
 * logger name its key equals or prefixes with `_`, filtered to the group's fields; one with no sample throws.
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @param {import("./definitions.js").MockSamples} samples
 * @returns {import("./definitions.js").MockDeviceData}
 */
export function composeMockData(defs, samples) {
    /** @type {import("./definitions.js").MockDeviceData} */
    const data = {
        measurements: {}, sensorsConfig: {}, networkingConfig: {}, systemConfig: {}, notificationConfig: {},
        status: { networking: {}, system: {}, sensors: {}, notification: {}, errcount: {} },
    };
    for (const section of defs.sections) {
        for (const group of section.groups) {
            const where = `${section.key}/${group.key}`;
            if (!("fields" in group)) {
                composeErrcountGroup(data, samples, group, where);
                continue;
            }
            composeGroup(data, samples, section.key, group, where);
        }
    }
    return data;
}

/**
 * Installs the mock fetch and returns an uninstall function. Only the routes the definitions declare are
 * intercepted - everything else passes through to the real fetch(). `controls` lets a test inject one
 * failure or a fixed delay, exercising error handling against more than a raw fetch stub.
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @param {import("./definitions.js").MockDeviceData} initialData
 * @param {MockFetchControls} [controls]
 * @returns {() => void}
 */
export function installMockFetch(defs, initialData, controls) {
    const state = structuredClone(initialData);
    /** @type {PutContext} */
    const context = { status: state.status, busyUntil: 0, busyRefused: false };
    const routes = routesOf(defs);
    const knownRoutes = [...new Set([...routes.get.keys(), ...routes.put.keys()])];
    const sensorFieldDefs = sensorFieldDefsFor(defs);
    const flatFieldDefs = new Map(defs.sections.map((section) => [section.key, flatFieldDefsFor(section)]));

    const originalFetch = window.fetch;
    window.fetch = async (input, init) => {
        const url = typeof input === "string" ? input : input.toString();
        const route = knownRoutes.find((candidate) => url === candidate || url.startsWith(`${candidate}?`));
        if (route === undefined) {
            return originalFetch(input, init);
        }
        const injected = injectedFailure(controls);
        if (injected !== undefined) {
            return injected;
        }
        const delayMs = controls?.delayMs;
        if (delayMs) {
            await new Promise((resolve) => {
                setTimeout(resolve, delayMs);
            });
        }
        const method = init?.method ?? "GET";
        const getSection = routes.get.get(route);
        const putSection = routes.put.get(route);
        if (method === "GET" && getSection !== undefined) {
            return jsonResponse(handleGet(getSection));
        }
        if (method === "PUT" && putSection !== undefined) {
            return jsonResponse(isJsonRequest(init) ? handlePut(putSection, String(init?.body ?? "")) : makeResponse(1));
        }
        return jsonResponse(makeResponse(405), 405);
    };

    /**
     * One GET answer: measurements jitter with each TS set to the clock, uptimes step and saturate, the
     * clock's Unix time goes into UnixTime and WifiTS unless that source is the unavailable marker, and
     * every mask: true field is masked.
     * @param {import("./definitions.js").Section} section
     * @returns {unknown}
     */
    function handleGet(section) {
        const unixTime = Math.floor(Date.now() / 1000);
        if (section.key === "measurements") {
            jitterEachSensorGroup(state.measurements);
            for (const body of Object.values(state.measurements)) {
                body.TS = unixTime;
            }
            return state.measurements;
        }
        if (section.key === "sensors") {
            return state.sensorsConfig;
        }
        if (section.key === "status") {
            stepCounter(state.status.system, "SysUptime");
            stepCounter(state.status.networking, "WifiUptime");
            // A source the server sent as the unavailable marker stays exactly that marker.
            if (!isUnavailable(state.status.system)) {
                state.status.system.UnixTime = unixTime;
            }
            if (!isUnavailable(state.status.networking)) {
                state.status.networking.WifiTS = unixTime;
            }
            return state.status;
        }
        const answer = { ...flatConfigOf(section.key) };
        for (const field of fieldsOf(section).filter((candidate) => candidate.mask === true)) {
            answer[field.key] = "********"; // Mirrors the server's masked GET: a credential is never returned (SPECIFICATION.md A.8).
        }
        return answer;
    }

    /**
     * One PUT answer, every outcome inside make_response(0): an unparseable or non-object body is
     * make_response(1), and an injected group failure answers every attempted key "Failed".
     * @param {import("./definitions.js").Section} section
     * @param {string} rawBodyText
     * @returns {{res: string, code: number, descr: string, result: Record<string, unknown>}}
     */
    function handlePut(section, rawBodyText) {
        const body = parseBody(rawBodyText);
        if (body === undefined) {
            return makeResponse(1);
        }
        const groupFailure = controls?.nextFailure === "group-failure";
        if (controls !== undefined && groupFailure) {
            controls.nextFailure = undefined;
        }
        context.busyRefused = false;
        const results = putResults(section, body);
        const result = groupFailure ? failEvery(results) : results;
        // The server's retry hint when the LED refused a command as busy.
        return makeResponse(0, context.busyRefused ? { descr: LED_BUSY_DESCR, result } : { result });
    }

    /**
     * Each PUT route's per-key words, as the server's handler for that route answers them.
     * @param {import("./definitions.js").Section} section
     * @param {Record<string, unknown>} body
     * @returns {Record<string, unknown>}
     */
    function putResults(section, body) {
        if (section.key === "sensors") {
            return putSensors(body);
        }
        if (section.key === "status") {
            return putStatus(body);
        }
        return applySparsePut(body, flatFieldDefs.get(section.key) ?? new Map(), flatConfigOf(section.key), context);
    }

    /**
     * @param {Record<string, unknown>} body
     * @returns {Record<string, unknown>}
     */
    function putSensors(body) {
        /** @type {Record<string, unknown>} */
        const results = {};
        for (const [sensorKey, entry] of Object.entries(body)) {
            const sensorDefs = sensorFieldDefs.get(sensorKey);
            if (sensorDefs === undefined || !isRecord(entry)) {
                // An unknown sensor, or an entry that is not an object, answers "Invalid" in place of its field map.
                results[sensorKey] = INVALID;
                continue;
            }
            state.sensorsConfig[sensorKey] ??= {};
            results[sensorKey] = applySparsePut(entry, sensorDefs, state.sensorsConfig[sensorKey], context);
        }
        return results;
    }

    /**
     * {"ResetErrors": true} refills every errcount entry and answers "Valid", as _put_status() does (SPECIFICATION.md A.8);
     * another dispatch key the section lists (a registered command) answers {key: true} "Valid"; any other value or key is
     * "Invalid". Stateless, it answers as a running device outside its "Failed" windows (pending command, reboot, mempause).
     * @param {Record<string, unknown>} body
     * @returns {Record<string, string>}
     */
    function putStatus(body) {
        /** @type {Record<string, string>} */
        const results = {};
        for (const [key, value] of Object.entries(body)) {
            if (key !== "ResetErrors" || value !== true) {
                results[key] = key !== "ResetErrors" && value === true && flatFieldDefs.get("status")?.get(key)?.dispatch === true ? VALID : INVALID;
                continue;
            }
            for (const entry of Object.values(state.status.errcount)) {
                entry.counter = 0;
                // Real reset() (src/asy_print_log.py) refills the fixed-length history with "no
                // error" placeholders, it never shrinks/empties the array.
                entry.history = (entry.history ?? []).map(() => ({ num: 0, type: "N" }));
            }
            results[key] = VALID;
        }
        return results;
    }

    /**
     * A flat section's stored config; a section the composed data has no config for stores into a fresh one.
     * @param {string} sectionKey
     * @returns {Record<string, unknown>}
     */
    function flatConfigOf(sectionKey) {
        if (sectionKey === "networking" || sectionKey === "system" || sectionKey === "notification") {
            return state[/** @type {"networkingConfig" | "systemConfig" | "notificationConfig"} */ (`${sectionKey}Config`)];
        }
        return {};
    }

    return () => {
        window.fetch = originalFetch;
    };
}
