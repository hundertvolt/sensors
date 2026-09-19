/**
 * Enumerates every real writable field across a device's own definitions.json, shared by the
 * mock-server and live-backend PUT-matrix tests so both run off one field-enumeration source
 * rather than two hand-kept copies of the same section/group/field-kind filtering.
 */

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").MockDeviceData} MockDeviceData */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Dispatch-only fields (a command/action, not a stored setting) and the one composite field shape
// (lightCmdLED) have their own distinct Invalid/Failed/Valid semantics, covered by dedicated tests
// elsewhere (mock-server.test.js, render.test.js) - excluded from this generic enumeration rather
// than force-fit into categories that don't apply to them.
export const DISPATCH_ONLY_KEYS = new Set(["SystemCmd", "PauseTime", "lightCmdLED", "ResetErrors"]);

/**
 * @typedef {{
 *   device: string, defs: SiteDefinitions, sectionKey: string, groupKey: string, field: FieldDef,
 *   putPath: string, currentValue: unknown,
 * }} PutFieldCase
 */

/**
 * Deterministic round-robin partition of `cases` into `count` shards, 1-indexed. CI runs the live
 * PUT matrix as parallel shard jobs; `spec` unset (a plain local run) returns every case.
 * @param {PutFieldCase[]} cases
 * @param {string | undefined} spec "<index>/<count>", e.g. "2/3"
 * @returns {PutFieldCase[]}
 */
export function shardPutFieldCases(cases, spec) {
    if (!spec) {
        return cases;
    }
    const parts = spec.split("/").map(Number);
    const index = parts[0] ?? 0;
    const count = parts[1] ?? 0;
    if (parts.length !== 2 || !Number.isInteger(index) || !Number.isInteger(count) || index < 1 || index > count) {
        throw new Error(`PUT matrix shard spec must be "<index>/<count>" with 1 <= index <= count, got ${spec}`);
    }
    return cases.filter((_case, position) => position % count === index - 1);
}

/**
 * @param {string} device
 * @param {SiteDefinitions} defs
 * @param {MockDeviceData} data current stored config, MockDeviceData-shaped
 * ({sensorsConfig, networkingConfig, systemConfig, notificationConfig}) - a real GET response set
 * reshaped into this same shape works identically (see live-backend-put-matrix.test.js).
 * @returns {PutFieldCase[]}
 */
export function collectPutFieldCases(device, defs, data) {
    /** @type {PutFieldCase[]} */
    const cases = [];
    for (const section of defs.sections) {
        if (!["sensors", "networking", "system", "notification"].includes(section.key) || section.rest.put === undefined) {
            continue; // measurements has no PUT; status's only field (ResetErrors) is dispatch-only
        }
        for (const group of section.groups) {
            if (!("fields" in group) || !group.submit) {
                continue;
            }
            for (const field of group.fields) {
                if (field.kind === "readonly" || field.kind === "composite" || DISPATCH_ONLY_KEYS.has(field.key)) {
                    continue;
                }
                const storedConfig =
                    section.key === "sensors"
                        ? data.sensorsConfig[group.key]
                        : /** @type {Record<string, unknown>} */ (data[/** @type {"networkingConfig"|"systemConfig"|"notificationConfig"} */ (`${section.key}Config`)]);
                cases.push({
                    device,
                    defs,
                    sectionKey: section.key,
                    groupKey: group.key,
                    field,
                    putPath: section.rest.put,
                    currentValue: storedConfig?.[field.key],
                });
            }
        }
    }
    return cases;
}
