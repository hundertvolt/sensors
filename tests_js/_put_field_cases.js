/**
 * Enumerates every real writable field across a device's own definitions.json - shared by
 * tests_js/mock-server-put-matrix.test.js (exhaustive matrix against js/mock-server.js's fake
 * fetch) and tests_js/live-backend-put-matrix.test.js (the same matrix's shape, against the real
 * digital-twin backend) so both stay driven by one field-enumeration source rather than two
 * hand-kept copies of the same section/group/field-kind filtering logic.
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
