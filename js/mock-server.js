/**
 * Prototype-only fake backend: intercepts `window.fetch()` for the six real REST paths
 * (SPECIFICATION.md Part A.8) and answers from an in-memory fixture. Replaced by the digital
 * twin's real server per SPECIFICATION.md Part H.7 - everything outside this file targets the real API.
 */

import { neverUnchanged } from "./definitions.js";

const REST_PATHS = /** @type {const} */ ([
    "/measurements",
    "/sensors",
    "/networking",
    "/system",
    "/notification",
    "/status",
]);

const SYSTEM_CMDS = ["reboot", "bootloader", "mempause"];
const PAUSE_TIME_MAX = 3600; // matches src/asy_webserver_service.py's own _PAUSE_TIME_MAX

/**
 * One rule per string shape, the same as src/asy_wifi_service.py's _host_label_ok()/_country_ok().
 * @type {Record<string, (value: string) => boolean>}
 */
const STRING_SHAPE_OK = {
    hostLabel: (value) => /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(value),
    countryCode: (value) => /^[A-Z]{2}$/.test(value),
};

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
        // PresOvers), and needs the same int-only strictness as an ordinary int field (unlike
        // SystemCmd's string-valued options, dispatched separately via SYSTEM_CMDS.includes()).
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
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @param {string} sectionKey
 * @returns {Map<string, import("./definitions.js").FieldDef>}
 */
function flatFieldDefsFor(defs, sectionKey) {
    const section = defs.sections.find((entry) => entry.key === sectionKey);
    /** @type {Map<string, import("./definitions.js").FieldDef>} */
    const map = new Map();
    for (const group of section?.groups ?? []) {
        if (!("fields" in group)) {
            continue; // an ErrcountGroup, not a FieldGroup
        }
        for (const field of group.fields) {
            map.set(field.key, field);
        }
    }
    return map;
}

/**
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
        bySensor.set(
            group.key,
            new Map(group.fields.map((/** @type {import("./definitions.js").FieldDef} */ field) => [field.key, field])),
        );
    }
    return bySensor;
}

/**
 * @param {Record<string, unknown>} body
 * @param {Map<string, import("./definitions.js").FieldDef>} fieldDefs
 * @param {Record<string, unknown>} storedConfig
 * @returns {Record<string, string>}
 */
function applySparsePut(body, fieldDefs, storedConfig) {
    /** @type {Record<string, string>} */
    const results = {};
    for (const [key, rawValue] of Object.entries(body)) {
        const field = fieldDefs.get(key);
        if (field === undefined) {
            continue; // unknown field - silently ignored, matches ConfigManager's own convention
        }
        if (field.kind === "composite") {
            let allValid = true;
            for (const subField of field.subFields ?? []) {
                const subValue = /** @type {Record<string, unknown>} */ (rawValue)?.[subField.key];
                if (!coerceAndValidate(subField, subValue).valid) {
                    allValid = false;
                }
            }
            results[key] = allValid ? "Valid" : "Invalid";
            continue;
        }
        const { valid, value } = coerceAndValidate(field, rawValue);
        if (!valid) {
            results[key] = "Invalid";
            continue;
        }
        if (storedConfig[key] === value) {
            results[key] = "Unchanged";
        } else {
            storedConfig[key] = value;
            results[key] = "Valid";
        }
    }
    return results;
}

/**
 * Dispatches a client-supplied number into `dest[destKey]`: range-validated but never compared
 * against a stored value, matching a real dispatched action (PauseTime) that never reports
 * "Unchanged" the way a genuine persisted setting does.
 * @param {unknown} rawValue
 * @param {number} min
 * @param {number} max
 * @param {Record<string, unknown>} dest
 * @param {string} destKey
 * @returns {string}
 */
function dispatchRangedAction(rawValue, min, max, dest, destKey) {
    if (typeof rawValue !== "number" || !Number.isFinite(rawValue) || !Number.isInteger(rawValue) || rawValue < min || rawValue > max) {
        return "Invalid";
    }
    dest[destKey] = rawValue;
    return "Valid";
}

// Legacy's own led_cmd() bounds (the legacy firmware's sensortask module, legacy/firmware/modules/),
// now enforced server-side too (src/sensortask_wozi.py's _notification_led_callback(), synthetic
// FieldSchema records) instead of silently clamping/flooring - see this function's docstring below.
const LIGHT_CMD_LED_RGB_MIN = 0;
const LIGHT_CMD_LED_RGB_MAX = 255;
const LIGHT_CMD_LED_T_MIN = 0.5;
const LIGHT_CMD_LED_T_MAX = 60.0;

/**
 * Dispatches LightCmdLED (SPECIFICATION.md Part A.8), never persisted: "Invalid" for a non-object;
 * "Failed" for a bad R/G/B (int, 0-255) or T (float, 0.5-60.0), and for a well-formed flash arriving
 * before the last started one's T has passed (the device refuses it while a signal runs); else "Valid".
 * @param {unknown} rawValue
 * @param {{busyUntil: number}} led
 * @returns {string}
 */
function dispatchLightCmdLed(rawValue, led) {
    if (typeof rawValue !== "object" || rawValue === null || Array.isArray(rawValue)) {
        return "Invalid";
    }
    const payload = /** @type {Record<string, unknown>} */ (rawValue);
    for (const key of ["R", "G", "B"]) {
        const num = payload[key];
        if (
            typeof num !== "number" ||
            !Number.isFinite(num) ||
            !Number.isInteger(num) ||
            num < LIGHT_CMD_LED_RGB_MIN ||
            num > LIGHT_CMD_LED_RGB_MAX
        ) {
            return "Failed";
        }
    }
    const { T: t } = payload;
    if (typeof t !== "number" || !Number.isFinite(t) || t < LIGHT_CMD_LED_T_MIN || t > LIGHT_CMD_LED_T_MAX) {
        return "Failed";
    }
    if (Date.now() < led.busyUntil) {
        return "Failed";
    }
    led.busyUntil = Date.now() + t * 1000;
    return "Valid";
}

/**
 * One never-"Unchanged" /sensors PUT value (neverUnchanged()): "Valid"/"Invalid" only, no real I2C
 * bus to fail. An always-executed field is also stored (AmbPres reads back what was applied); a
 * dispatch field never is, so a later GET cannot echo a command back as a setting.
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @param {Record<string, unknown>} storedConfig
 * @returns {string}
 */
function dispatchSensorQuirkField(field, rawValue, storedConfig) {
    const { valid, value } = coerceAndValidate(field, rawValue);
    if (valid && field.alwaysExecuted === true) {
        storedConfig[field.key] = value;
    }
    return valid ? "Valid" : "Invalid";
}

/**
 * Applies the real GET-readback quirks: `ForceCalRef` always reports 400
 * (SCD30's volatile register), and the three command-only triggers are omitted entirely as the
 * real schema omits them - echoing one back would make it look like a stored setting.
 * @param {Record<string, Record<string, unknown>>} sensorsConfig
 * @returns {Record<string, Record<string, unknown>>}
 */
function applySensorQuirksForGet(sensorsConfig) {
    /** @type {Record<string, Record<string, unknown>>} */
    const result = {};
    for (const [sensorKey, fields] of Object.entries(sensorsConfig)) {
        const rest = Object.fromEntries(
            Object.entries(fields).filter(([key]) => key !== "ContMeas" && key !== "ResetVOC" && key !== "Calibrate"),
        );
        result[sensorKey] = "ForceCalRef" in rest ? { ...rest, ForceCalRef: 400 } : rest;
    }
    return result;
}

/**
 * Simulates the backend's known gap (Part H.6): a settings group's post-write hook raising
 * drops that group's fields from `result` while the response still says `res:"OK"`. Deletes one
 * key in place, once, on `controls.nextFailure === "partial-result"`, consumed either way.
 * @param {Record<string, string>} results
 * @param {MockFetchControls} [controls]
 */
function dropOneResultForPartialFailure(results, controls) {
    if (controls?.nextFailure !== "partial-result") {
        return;
    }
    controls.nextFailure = undefined;
    const [key] = Object.keys(results);
    if (key !== undefined) {
        delete results[key];
    }
}

/**
 * @param {Record<string, unknown>} result
 * @returns {{res: string, code: number, descr: string, result: Record<string, unknown>}}
 */
function envelope(result) {
    return { res: "OK", code: 0, descr: "OK", result };
}

/**
 * Nudges every numeric leaf in a measurement record by a small random jitter, so polled values
 * visibly move like a real sensor instead of sitting static. Timestamp-looking keys (ending "TS"
 * or named "Timestamp") always increment instead of jittering.
 *
 * Recurses into a nested sub-object (`{"RGB": {"R": 0.5}}`), which the ISL29125's own body is the
 * first to produce: without this those leaves would sit static forever, which reads as a broken
 * renderer rather than as a mock-server gap.
 * @param {Record<string, unknown>} group
 */
function jitterInPlace(group) {
    for (const [key, value] of Object.entries(group)) {
        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
            jitterInPlace(/** @type {Record<string, unknown>} */ (value));
            continue;
        }
        if (typeof value !== "number") {
            continue;
        }
        if (key.endsWith("TS") || key === "Timestamp" || key.endsWith("Uptime")) {
            group[key] = value + 1;
        } else {
            // Spread and rounding were sized for readings of order hundreds (CO2 ~600). On the
            // ISL29125's normalised 0-1 leaves a 0.05 floor is +-178%, taking them NEGATIVE, and
            // two decimals quantise to 0.00. Below 1 both scale with the value; above it, nothing.
            const magnitude = Math.abs(value);
            const spread = magnitude >= 1 ? Math.max(magnitude * 0.01, 0.05) : magnitude * 0.05;
            const factor = magnitude >= 1 ? 100 : 10000;
            group[key] = Math.round((value + (Math.random() * 2 - 1) * spread) * factor) / factor;
        }
    }
}

/**
 * One-shot failure to inject into the next intercepted REST request (see SPECIFICATION.md
 * Part H.6 for the settings-group-failure rationale behind one of these variants).
 * Consumed and cleared after firing once.
 * @typedef {"network" | number | "malformed-body" | "torn-json" | "empty-body" | "partial-result"} MockFailure
 * @typedef {{nextFailure?: MockFailure | undefined}} MockFetchControls
 */

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
 * The maintenance group's `<SAMPLE>_<field>` keys, filled from `status.sensors.<SAMPLE>.<field>`.
 * @param {Record<string, Record<string, unknown>>} samples
 * @param {import("./definitions.js").FieldDef[]} fields
 * @param {string} where
 * @returns {Record<string, Record<string, unknown>>}
 */
function composeMaintenance(samples, fields, where) {
    /** @type {Record<string, Record<string, unknown>>} */
    const bySample = {};
    for (const field of fields) {
        const name = sampleNameFor(Object.keys(samples), field.key);
        const source = name === undefined ? undefined : samples[name];
        if (name === undefined || source === undefined) {
            throw new Error(`mock samples: no sample for group "${where}"`);
        }
        const leaf = field.key.slice(name.length + 1);
        bySample[name] ??= {};
        if (leaf in source) {
            bySample[name][leaf] = structuredClone(source[leaf]);
        }
    }
    return bySample;
}

/**
 * Builds one device's mock data: each group takes the sample of the driver whose logger name its
 * key equals or prefixes with `_`, filtered to the group's fields.
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
                for (const module of group.modules) {
                    const name = sampleNameFor(Object.keys(samples.errcount), module.key);
                    data.status.errcount[module.key] = structuredClone((name === undefined ? undefined : samples.errcount[name]) ?? { counter: 0, history: [] });
                }
                continue;
            }
            composeGroup(data, samples, section.key, group, where);
        }
    }
    return data;
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
        copyNamedFields(source, group.fields, /** @type {Record<string, unknown>} */ (dest[group.key]));
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
 * Installs the mock fetch and returns an uninstall function. Only REST_PATHS are intercepted -
 * everything else passes through to the real fetch(). `controls`
 * lets a test inject one failure, exercising error-handling against more than a raw fetch stub.
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @param {import("./definitions.js").MockDeviceData} initialData
 * @param {MockFetchControls} [controls]
 * @returns {() => void}
 */
export function installMockFetch(defs, initialData, controls) {
    const state = structuredClone(initialData);
    const led = { busyUntil: 0 }; // when the last LightCmdLED flash started here ends (Date.now() ms)
    const sensorFieldDefs = sensorFieldDefsFor(defs);
    const flatDefsByEndpoint = {
        networking: flatFieldDefsFor(defs, "networking"),
        system: flatFieldDefsFor(defs, "system"),
        notification: flatFieldDefsFor(defs, "notification"),
    };

    const originalFetch = window.fetch;
    window.fetch = async (input, init) => {
        const url = typeof input === "string" ? input : input.toString();
        const path = /** @type {(typeof REST_PATHS)[number] | undefined} */ (
            REST_PATHS.find((candidate) => url === candidate || url.startsWith(`${candidate}?`))
        );
        if (path === undefined) {
            return originalFetch(input, init);
        }

        if (controls?.nextFailure !== undefined && controls.nextFailure !== "partial-result") {
            const failure = controls.nextFailure;
            controls.nextFailure = undefined;
            if (failure === "network") {
                throw new TypeError("Failed to fetch (simulated network failure)");
            }
            if (failure === "malformed-body") {
                // Matches the backend's own make_response(1) (Part A.8/A.5): a body Request.json
                // cannot parse, or that parses to something other than an object, is a clean
                // HTTP 200 with res:"ERR" rather than a shaped HTTP error status.
                return jsonResponse({ res: "ERR", code: 1, descr: "Invalid JSON request", result: {} });
            }
            if (failure === "torn-json") {
                // A connection dropped/corrupted mid-response: HTTP succeeds but the body isn't
                // valid JSON - a genuine transmission error, not a request the backend rejected.
                return new Response("{\"res\": \"OK\", \"code\": 0, tru", { status: 200 });
            }
            if (failure === "empty-body") {
                return new Response("", { status: 200 });
            }
            return jsonResponse({ res: "ERR", code: 5, descr: "Simulated failure" }, failure);
        }

        await new Promise((resolve) => {
            setTimeout(resolve, 80 + Math.random() * 120);
        });
        const method = init?.method ?? "GET";
        const rawBodyText = String(init?.body ?? "{}");
        /** @returns {Record<string, unknown>} */
        const body = () => JSON.parse(rawBodyText);

        if (method === "GET") {
            return jsonResponse(handleGet(path));
        }
        if (method === "PUT" && path === "/sensors") {
            /** @type {Record<string, Record<string, string>>} */
            const results = {};
            for (const [sensorKey, fields] of Object.entries(body())) {
                const sensorDefs = sensorFieldDefs.get(sensorKey);
                if (sensorDefs === undefined) {
                    continue;
                }
                state.sensorsConfig[sensorKey] ??= {};
                const stored = state.sensorsConfig[sensorKey];
                const rawFields = /** @type {Record<string, unknown>} */ (fields);
                // The never-"Unchanged" fields (from the definitions' flags) leave the generic
                // compare-and-store path, which would answer "Unchanged" for a repeated value.
                const isQuirk = (/** @type {string} */ key) => {
                    const field = sensorDefs.get(key);
                    return field !== undefined && neverUnchanged(field);
                };
                const persistableFields = Object.fromEntries(Object.entries(rawFields).filter(([key]) => !isQuirk(key)));
                const sensorResults = applySparsePut(persistableFields, sensorDefs, stored);
                for (const [quirkKey, rawValue] of Object.entries(rawFields)) {
                    const field = sensorDefs.get(quirkKey);
                    if (field !== undefined && neverUnchanged(field)) {
                        sensorResults[quirkKey] = dispatchSensorQuirkField(field, rawValue, stored);
                    }
                }
                results[sensorKey] = sensorResults;
            }
            for (const perSensorResult of Object.values(results)) {
                dropOneResultForPartialFailure(perSensorResult, controls);
            }
            return jsonResponse(envelope(results));
        }
        if (method === "PUT" && (path === "/networking" || path === "/system" || path === "/notification")) {
            const endpointKey = /** @type {"networking" | "system" | "notification"} */ (path.slice(1));
            const configKey = /** @type {"networkingConfig" | "systemConfig" | "notificationConfig"} */ (`${endpointKey}Config`);
            const rawBody = body();
            // SystemCmd/PauseTime/LightCmdLED are dispatched actions, never persisted settings
            // (Part A.8). Excluded before the generic sparse-PUT path so none reaches
            // state[configKey], which is what keeps a later GET matching _get_settings_flat().
            const { SystemCmd, PauseTime, LightCmdLED, ...persistableBody } = rawBody;
            const results = applySparsePut(persistableBody, flatDefsByEndpoint[endpointKey], state[configKey]);
            if (path === "/system" && "SystemCmd" in rawBody) {
                results.SystemCmd = typeof SystemCmd === "string" && SYSTEM_CMDS.includes(SystemCmd) ? "Valid" : "Invalid";
            }
            if (path === "/notification" && "PauseTime" in rawBody) {
                results.PauseTime = dispatchRangedAction(PauseTime, 0, PAUSE_TIME_MAX, state.status.notification, "PauseTime");
            }
            if (path === "/notification" && "LightCmdLED" in rawBody) {
                results.LightCmdLED = dispatchLightCmdLed(LightCmdLED, led);
            }
            dropOneResultForPartialFailure(results, controls);
            return jsonResponse(envelope(results));
        }
        if (method === "PUT" && path === "/status") {
            if (body().ResetErrors === true) {
                for (const entry of Object.values(state.status.errcount)) {
                    entry.counter = 0;
                    // Real reset() (src/asy_print_log.py) refills the fixed-length history with "no
                    // error" placeholders, it never shrinks/empties the array.
                    entry.history = (entry.history ?? []).map(() => ({ num: 0, type: "N" }));
                }
            }
            return jsonResponse({ res: "OK", code: 0, descr: "OK" });
        }
        return jsonResponse({ res: "ERR", code: 4, descr: "Method not allowed" }, 405);
    };

    /**
     * @param {(typeof REST_PATHS)[number]} path
     * @returns {unknown}
     */
    function handleGet(path) {
        if (path === "/measurements") {
            jitterEachSensorGroup(state.measurements);
            return state.measurements;
        }
        if (path === "/sensors") {
            return applySensorQuirksForGet(state.sensorsConfig);
        }
        if (path === "/networking") {
            // Mirrors the _mask_pw() overlays of src/asy_wifi_service.py and src/asy_mqtt_client.py: a real
            // credential is never returned in plaintext over GET, on real hardware or here.
            return { ...state.networkingConfig, PW: "********", ...("MQTTPW" in state.networkingConfig ? { MQTTPW: "********" } : {}) };
        }
        if (path === "/system") {
            return state.systemConfig;
        }
        if (path === "/notification") {
            return state.notificationConfig;
        }
        // /status
        jitterInPlace(state.status.networking);
        jitterInPlace(state.status.system);
        return state.status;
    }

    return () => {
        window.fetch = originalFetch;
    };
}

/**
 * jitterInPlace mutates numeric leaves of a flat object; measurements are one level deeper
 * (per-sensor sub-objects), so jitter each sensor's own leaf object individually.
 * @param {Record<string, Record<string, unknown>>} bySensor
 */
function jitterEachSensorGroup(bySensor) {
    for (const sensorGroup of Object.values(bySensor)) {
        jitterInPlace(sensorGroup);
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
