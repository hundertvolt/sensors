/**
 * Enumerates every real writable field across a device's own definitions.json, shared by the
 * mock-server and live-backend PUT-matrix tests so both run off one field-enumeration source
 * rather than two hand-kept copies of the same section/group/field-kind filtering.
 */

import { neverUnchanged } from "../js/definitions.js";

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("../js/definitions.js").MockDeviceData} MockDeviceData */
/** @typedef {import("../js/definitions.js").FieldDef} FieldDef */

// Action fields (dispatch) and always-executed fields have their own category: the matrices'
// never-"Unchanged" category (two identical valid sends both answer Valid).

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
                if (field.kind === "readonly" || field.kind === "composite" || neverUnchanged(field)) {
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

/**
 * The key up to its first `_`: the driver's logger name an instance key extends (`SCD30_primary`).
 * @param {string} key
 * @returns {string}
 */
function driverBase(key) {
    const cut = key.indexOf("_");
    return cut === -1 ? key : key.slice(0, cut);
}

/**
 * Keeps the first case per section, driver and identical field definition, so a field every
 * device shares runs once; a field differing in any attribute runs again.
 * @template {PutFieldCase} T
 * @param {T[]} cases
 * @returns {T[]}
 */
export function dedupePutFieldCases(cases) {
    const seen = new Set();
    return cases.filter((testCase) => {
        const signature = `${testCase.sectionKey}|${driverBase(testCase.groupKey)}|${JSON.stringify(testCase.field)}`;
        if (seen.has(signature)) {
            return false;
        }
        seen.add(signature);
        return true;
    });
}

/**
 * A valid string of about `length` characters for `field`'s shape: the matrices' "valid" probes.
 * @param {FieldDef} field
 * @param {number} length
 * @returns {string}
 */
export function validStringValue(field, length) {
    if (field.shape === "countryCode") {
        return "XX"; // cyw43's worldwide code: the one alpha-2 pair valid on every device
    }
    return "x".repeat(length);
}
