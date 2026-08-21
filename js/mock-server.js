/**
 * Prototype-only fake backend (WEBSITE_PLAN.md §10 session 2). No live device/backend exists
 * yet - this module intercepts `window.fetch()` for the six real REST paths from
 * SPECIFICATION.md Part A.8 and answers from an in-memory mock-data fixture, so the poll-manager/
 * renderer exercise the exact same request shapes they will against a real backend later.
 * Will be replaced by the digital-twin's real live server in a future session (WEBSITE_PLAN.md §7) -
 * everything outside this one file is written against the real REST contract, not this mock.
 */

const REST_PATHS = /** @type {const} */ ([
    "/measurements",
    "/sensors",
    "/networking",
    "/system",
    "/notification",
    "/status",
]);

const SYSTEM_CMDS = ["reboot", "bootloader", "mempause"];

/**
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @returns {{valid: boolean, value: unknown}}
 */
function coerceAndValidate(field, rawValue) {
    if (field.kind === "number") {
        const value = typeof rawValue === "number" ? rawValue : Number(rawValue);
        if (!Number.isFinite(value)) {
            return { valid: false, value };
        }
        const specialValues = field.specialValues ?? [];
        if (specialValues.some((special) => special.value === value)) {
            return { valid: true, value };
        }
        const min = field.min ?? -Infinity;
        const max = field.max ?? Infinity;
        return { valid: value >= min && value <= max, value };
    }
    if (field.kind === "string") {
        const value = String(rawValue);
        const minLength = field.minLength ?? 0;
        const maxLength = field.maxLength ?? Infinity;
        return { valid: value.length >= minLength && value.length <= maxLength, value };
    }
    if (field.kind === "enum") {
        // Compare as-sent, not string-coerced: an enum's real value can be numeric (e.g. BMP3XX's
        // PressOvers) - a real backend expects that type back, not "4" where it wrote 4.
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

/** @param {Record<string, unknown>} result */
function envelope(result) {
    return { res: "OK", code: 0, descr: "OK", result };
}

/**
 * Nudges every numeric leaf in a plain (non-nested-object-of-objects) record by a small random
 * jitter, so polled values visibly move like a real sensor instead of sitting static. Timestamp-
 * looking keys (ending "TS" or named "Timestamp") always increment instead of jittering.
 * @param {Record<string, unknown>} group
 */
function jitterInPlace(group) {
    for (const [key, value] of Object.entries(group)) {
        if (typeof value !== "number") {
            continue;
        }
        if (key.endsWith("TS") || key === "Timestamp" || key.endsWith("Uptime")) {
            group[key] = value + 1;
        } else {
            const spread = Math.max(Math.abs(value) * 0.01, 0.05);
            group[key] = Math.round((value + (Math.random() * 2 - 1) * spread) * 100) / 100;
        }
    }
}

/**
 * One-shot failure to inject into the next intercepted REST request - `"network"` makes the mock
 * fetch reject the way a real dropped/hung connection would; a number makes it resolve with that
 * HTTP status instead (a real backend error response). Consumed and cleared after firing once.
 * @typedef {{nextFailure?: "network" | number}} MockFetchControls
 */

/**
 * Installs the mock fetch and returns an uninstall function. Only paths in REST_PATHS are
 * intercepted - definitions.json and mock fixture files are ordinary relative fetches that pass
 * straight through to the real fetch(). `controls`, when passed, lets a test inject exactly one
 * failure into the next matched request (WEBSITE_PLAN.md §10 session 3 - exercising the
 * frontend's error-handling paths against something more realistic than a raw window.fetch stub).
 * @param {import("./definitions.js").SiteDefinitions} defs
 * @param {import("./definitions.js").MockDeviceData} initialData
 * @param {MockFetchControls} [controls]
 * @returns {() => void}
 */
export function installMockFetch(defs, initialData, controls) {
    const state = structuredClone(initialData);
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

        if (controls?.nextFailure !== undefined) {
            const failure = controls.nextFailure;
            controls.nextFailure = undefined;
            if (failure === "network") {
                throw new TypeError("Failed to fetch (simulated network failure)");
            }
            return jsonResponse({ res: "ERR", code: 5, descr: "Simulated failure" }, failure);
        }

        await new Promise((resolve) => setTimeout(resolve, 80 + Math.random() * 120));
        const method = init?.method ?? "GET";
        /** @returns {Record<string, any>} */
        const body = () => JSON.parse(String(init?.body ?? "{}"));

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
                results[sensorKey] = applySparsePut(fields, sensorDefs, state.sensorsConfig[sensorKey]);
            }
            return jsonResponse(envelope(results));
        }
        if (method === "PUT" && (path === "/networking" || path === "/system" || path === "/notification")) {
            const endpointKey = /** @type {"networking" | "system" | "notification"} */ (path.slice(1));
            const configKey = /** @type {"networkingConfig" | "systemConfig" | "notificationConfig"} */ (`${endpointKey}Config`);
            const results = applySparsePut(body(), flatDefsByEndpoint[endpointKey], state[configKey]);
            if (path === "/system" && "SystemCmd" in body()) {
                const cmd = body().SystemCmd;
                results.SystemCmd = SYSTEM_CMDS.includes(cmd) ? "Valid" : "Invalid";
            }
            return jsonResponse(envelope(results));
        }
        if (method === "PUT" && path === "/status") {
            if (body().ResetErrors === true) {
                for (const entry of Object.values(state.status.errcount)) {
                    entry.counter = 0;
                    // Real reset() (src/print_log.py) refills the fixed-length history with "no
                    // error" placeholders, it never shrinks/empties the array.
                    entry.history = (entry.history ?? []).map(() => ({ num: 0, type: "N" }));
                }
            }
            return jsonResponse({ res: "OK", code: 0, descr: "OK" });
        }
        return jsonResponse({ res: "ERR", code: 4, descr: "Method not allowed" }, 405);
    };

    /** @param {(typeof REST_PATHS)[number]} path */
    function handleGet(path) {
        if (path === "/measurements") {
            jitterEachSensorGroup(state.measurements);
            return state.measurements;
        }
        if (path === "/sensors") {
            return state.sensorsConfig;
        }
        if (path === "/networking") {
            return state.networkingConfig;
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
 */
function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}
