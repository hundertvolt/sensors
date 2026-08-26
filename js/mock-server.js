/**
 * Prototype-only fake backend: intercepts `window.fetch()` for the six real REST paths
 * (SPECIFICATION.md Part A.8) and answers from an in-memory fixture. Replaced by the digital
 * twin's real server per WEBSITE_PLAN.md §7 - everything outside this file targets the real API.
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
const PAUSE_TIME_MAX = 3600; // matches src/asy_webserver_service.py's own _PAUSE_TIME_MAX

// Three /sensors fields with real, documented hardware quirks (WEBSITE_PLAN.md §7;
// src/asy_scd30_driver.py's _set_dict_cfg()/get_forced_recalibration_reference(),
// src/asy_sgp40_driver.py's _push_reset_voc()): each is a direct hardware dispatch re-run every
// request, never compared against a stored value ("Unchanged" can never fire) and never persisted
// the way an ordinary settings field is - modeled here instead of falling through to the generic
// store-and-echo path, which would wrongly report "Unchanged" on a resubmit and echo back whatever
// was just PUT rather than the real GET-readback quirk below.
const SENSOR_QUIRK_FIELDS = new Set(["ForceCalRef", "ContMeas", "SGPResetVOC"]);

/**
 * @param {import("./definitions.js").FieldDef} field
 * @param {unknown} rawValue
 * @returns {{valid: boolean, value: unknown}}
 */
function coerceAndValidate(field, rawValue) {
    if (field.kind === "number") {
        // No Number(rawValue) coercion: config_manager.py's type_or_range_error() does a strict
        // Python type() check before ever looking at magnitude, so a JSON string (even a
        // numeric-looking one like "42") is rejected outright server-side, never parsed. Garbage
        // text js/render.js's readInputValue() sends through unparsed (its own NaN-passthrough
        // fix) reaches here as a non-number too, so it still correctly ends up Invalid - just via
        // this type check now, not a NaN check.
        if (typeof rawValue !== "number" || !Number.isFinite(rawValue)) {
            return { valid: false, value: rawValue };
        }
        // Mirrors config_manager.py's coerce_numeric()/type_or_range_error() int<->float policy
        // (SPECIFICATION.md Part A.8): a field not marked field.float is int-typed server-side and
        // accepts only a value with no fractional part - not truncated/rounded, rejected outright,
        // same treatment as out-of-range. A float-typed field accepts any finite value regardless
        // of whether it's whole or fractional (int -> float is a blanket accept). JS has no
        // separate int/float runtime type to begin with, so unlike the old literal-shape check
        // (scanNumericLiteralShapes(), now removed), only the value's own integrality matters -
        // "5" and "5.0" both parse to the identical JS number, and both are now judged the same way.
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
        const value = rawValue;
        const minLength = field.minLength ?? 0;
        const maxLength = field.maxLength ?? Infinity;
        return { valid: value.length >= minLength && value.length <= maxLength, value };
    }
    if (field.kind === "enum") {
        // Compare as-sent, not string-coerced: an enum's real value can be numeric (e.g. BMP3XX's
        // PressOvers) - a real backend expects that type back, not "4" where it wrote 4. Every
        // currently-declared numeric enum is itself a plain type_or_range_error()-backed int field
        // with a special-value list (SPECIFICATION.md Part A.8's schema-comment grammar sketch,
        // "kind: enum" derivation), so it needs the same int-only strictness (reject a fractional
        // value) as an ordinary int-typed number field - unlike SystemCmd, whose string-valued
        // options never reach coerceAndValidate() at all (dispatched separately via
        // SYSTEM_CMDS.includes(), no type_or_range_error involved).
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
 * Dispatches a client-supplied number into `dest[destKey]`: range-validated (rejecting non-finite/
 * out-of-range as "Invalid") but never compared against a stored value - matches a real dispatched
 * action (SystemCmd, PauseTime), which the real backend re-runs fresh every call and never reports
 * "Unchanged" for, unlike a genuine persisted setting. This helper's only current caller
 * (PauseTime) is int-typed server-side (`_dispatch_notification_pause()` now reuses
 * config_manager.py's own type_or_range_error() against a synthetic FieldSchema,
 * SPECIFICATION.md Part A.8) - a fractional value is rejected, an integral one accepted, same
 * int<->float coercion policy as any other int-typed field.
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

// Legacy's own led_cmd() bounds (modules/sensortask-wozi.py), now enforced server-side too
// (src/sensortask_wozi.py's _notification_led_callback(), synthetic FieldSchema records) instead
// of silently clamping/flooring - see this function's own docstring below.
const LIGHT_CMD_LED_RGB_MIN = 0;
const LIGHT_CMD_LED_RGB_MAX = 255;
const LIGHT_CMD_LED_T_MIN = 0.5;
const LIGHT_CMD_LED_T_MAX = 60.0;

/**
 * Dispatches lightCmdLED (SPECIFICATION.md Part A.8): a fire-and-forget flash command, never a
 * persisted setting - matches src/asy_webserver_service.py's _dispatch_notification_led() +
 * src/sensortask_wozi.py's _notification_led_callback() exactly: "Invalid" only when the payload
 * isn't an object at all, "Failed" when r/g/b is missing/non-numeric/fractional/out-of-range
 * (0-255) or t is missing/non-numeric/out-of-range (0.5-60.0) - config_manager.py's
 * coerce_numeric()/type_or_range_error() policy (SPECIFICATION.md Part A.8): r/g/b are int-typed
 * and reject a fractional value the same way any other int-typed field does; t is float-typed and
 * accepts any finite in-range value. Legacy rejected out-of-range r/g/b/t outright too - the
 * promoted src/ backend used to silently clamp/floor instead, now closed to match.
 * @param {unknown} rawValue
 * @returns {string}
 */
function dispatchLightCmdLed(rawValue) {
    if (typeof rawValue !== "object" || rawValue === null || Array.isArray(rawValue)) {
        return "Invalid";
    }
    const payload = /** @type {Record<string, unknown>} */ (rawValue);
    for (const key of ["r", "g", "b"]) {
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
    const t = payload.t;
    if (typeof t !== "number" || !Number.isFinite(t) || t < LIGHT_CMD_LED_T_MIN || t > LIGHT_CMD_LED_T_MAX) {
        return "Failed";
    }
    return "Valid";
}

/**
 * Validates+dispatches one of SENSOR_QUIRK_FIELDS' PUT value exactly like the real driver's own
 * type_or_range_error()-then-direct-hardware-write path: "Valid"/"Invalid" only (never "Failed" -
 * there's no real I2C bus here to fail), and never written to storedConfig, so a later GET falls
 * through to applySensorQuirksForGet()'s own override/omission for these three keys instead of
 * echoing back whatever was just PUT. `field` is undefined when this device's schema doesn't
 * declare the key at all - treated the same as applySparsePut()'s own unknown-field tolerance.
 * @param {import("./definitions.js").FieldDef | undefined} field
 * @param {unknown} rawValue
 * @returns {string | undefined}
 */
function dispatchSensorQuirkField(field, rawValue) {
    if (field === undefined) {
        return undefined;
    }
    return coerceAndValidate(field, rawValue).valid ? "Valid" : "Invalid";
}

/**
 * Applies SENSOR_QUIRK_FIELDS' real GET-readback behavior to a /sensors response: `ForceCalRef`
 * always reports the fixed constant 400 regardless of what was last applied (SCD30's own volatile-
 * register limitation - get_forced_recalibration_reference()'s own docstring); `ContMeas`/
 * `SGPResetVOC` are omitted entirely, matching get_dict_cfg()'s explicit schema exclusion for both
 * (neither is ever in ConfigManager's cache to read back in the first place).
 * @param {Record<string, Record<string, unknown>>} sensorsConfig
 * @returns {Record<string, Record<string, unknown>>}
 */
function applySensorQuirksForGet(sensorsConfig) {
    /** @type {Record<string, Record<string, unknown>>} */
    const result = {};
    for (const [sensorKey, fields] of Object.entries(sensorsConfig)) {
        const rest = Object.fromEntries(Object.entries(fields).filter(([key]) => key !== "ContMeas" && key !== "SGPResetVOC"));
        result[sensorKey] = "ForceCalRef" in rest ? { ...rest, ForceCalRef: 400 } : rest;
    }
    return result;
}

/**
 * Simulates the real backend's own known gap (WEBSITE_PLAN.md §10 session 3 follow-up 2): a
 * settings group's post-write hook raising drops that group's fields from `result` entirely,
 * with the overall response still reporting `res:"OK"`. Deletes one arbitrary key in place, once,
 * only when `controls.nextFailure === "partial-result"` (consumed either way it fires or not).
 * @param {Record<string, string>} results
 * @param {MockFetchControls} [controls]
 */
function dropOneResultForPartialFailure(results, controls) {
    if (controls?.nextFailure !== "partial-result") {
        return;
    }
    controls.nextFailure = undefined;
    const key = Object.keys(results)[0];
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
 * One-shot failure to inject into the next intercepted REST request (WEBSITE_PLAN.md §10
 * session 3 follow-up 2 - see that entry for the full real-backend-error-taxonomy rationale
 * behind each variant). Consumed and cleared after firing once.
 * @typedef {"network" | number | "malformed-body" | "torn-json" | "empty-body" | "partial-result"} MockFailure
 * @typedef {{nextFailure?: MockFailure}} MockFetchControls
 */

/**
 * Installs the mock fetch and returns an uninstall function. Only REST_PATHS are intercepted -
 * everything else passes through to the real fetch(). `controls` (WEBSITE_PLAN.md §10 session 3)
 * lets a test inject one failure, exercising error-handling against more than a raw fetch stub.
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

        if (controls?.nextFailure !== undefined && controls.nextFailure !== "partial-result") {
            const failure = controls.nextFailure;
            controls.nextFailure = undefined;
            if (failure === "network") {
                throw new TypeError("Failed to fetch (simulated network failure)");
            }
            if (failure === "malformed-body") {
                // Matches the real backend's own make_response(1) exactly (SPECIFICATION.md Part
                // A.8/A.5): a request body Request.json can't parse, or that parses to something
                // other than a JSON object, is a clean HTTP 200 with res:"ERR" - never a shaped
                // HTTP error status.
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
                const rawFields = /** @type {Record<string, unknown>} */ (fields);
                // SENSOR_QUIRK_FIELDS are excluded before the generic sparse-PUT path below, same
                // shape as SystemCmd/PauseTime/lightCmdLED's own exclusion further down - none of
                // them are real persisted settings, so none should reach state.sensorsConfig.
                const persistableFields = Object.fromEntries(Object.entries(rawFields).filter(([key]) => !SENSOR_QUIRK_FIELDS.has(key)));
                const sensorResults = applySparsePut(persistableFields, sensorDefs, state.sensorsConfig[sensorKey]);
                for (const quirkKey of SENSOR_QUIRK_FIELDS) {
                    if (!(quirkKey in rawFields)) {
                        continue;
                    }
                    const status = dispatchSensorQuirkField(sensorDefs.get(quirkKey), rawFields[quirkKey]);
                    if (status !== undefined) {
                        sensorResults[quirkKey] = status;
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
            // SystemCmd/PauseTime/lightCmdLED are dispatched actions, never persisted settings on
            // the real backend (SPECIFICATION.md Part A.8) - excluded here before the generic
            // sparse-PUT path below so none of them leak into state[configKey] (and so a later GET
            // never returns them, matching _get_settings_flat()'s real behavior).
            const { SystemCmd, PauseTime, lightCmdLED, ...persistableBody } = rawBody;
            const results = applySparsePut(persistableBody, flatDefsByEndpoint[endpointKey], state[configKey]);
            if (path === "/system" && "SystemCmd" in rawBody) {
                results.SystemCmd = typeof SystemCmd === "string" && SYSTEM_CMDS.includes(SystemCmd) ? "Valid" : "Invalid";
            }
            if (path === "/notification" && "PauseTime" in rawBody) {
                results.PauseTime = dispatchRangedAction(PauseTime, 0, PAUSE_TIME_MAX, state.status.notification, "PauseTime");
            }
            if (path === "/notification" && "lightCmdLED" in rawBody) {
                results.lightCmdLED = dispatchLightCmdLed(lightCmdLED);
            }
            dropOneResultForPartialFailure(results, controls);
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
 * @returns {Response}
 */
function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}
