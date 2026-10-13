/**
 * The one tests_js loader for every device's generated definitions and REST reference (build/generated_src/);
 * throws at import when the tree is missing or does not name exactly the devices/*.toml set.
 */

/** @typedef {import("../js/definitions.js").SiteDefinitions} SiteDefinitions */
/**
 * @typedef {{
 *   device: string, envelopeCodes: Record<string, string>, resultWords: string[],
 *   routes: {method: string, path: string, groups: unknown[]}[],
 * }} ApiReference
 */

const definitionFiles = /** @type {Record<string, SiteDefinitions>} */ (
    import.meta.glob("../build/generated_src/definitions/*.json", { eager: true, import: "default" })
);
const referenceFiles = /** @type {Record<string, ApiReference>} */ (
    import.meta.glob("../build/generated_src/api/*.json", { eager: true, import: "default" })
);
const tomlFiles = import.meta.glob("../devices/*.toml", { query: "?raw", eager: true, import: "default" });

// The generated tree's files that describe no device: the manifest and the inputs stamp.
const NON_DEVICE_STEMS = new Set(["index", "inputs_stamp"]);

/**
 * @param {string} path
 * @returns {string}
 */
function stemOf(path) {
    const name = path.slice(path.lastIndexOf("/") + 1);
    return name.slice(0, name.lastIndexOf("."));
}

/** Sorted devices/*.toml stems, test fixtures (zz_test_*) dropped as tests_scripts/_devices.py drops them. */
export const DEVICE_IDS = Object.keys(tomlFiles)
    .map(stemOf)
    .filter((id) => !id.startsWith("zz_test_"))
    .sort();

/** @type {Map<string, SiteDefinitions>} */
export const GENERATED_DEFINITIONS = new Map(
    Object.entries(definitionFiles)
        .map(([path, defs]) => /** @type {[string, SiteDefinitions]} */ ([stemOf(path), defs]))
        .filter(([id]) => !NON_DEVICE_STEMS.has(id))
        .sort(([a], [b]) => (a < b ? -1 : 1)),
);

/** @type {Map<string, ApiReference>} */
export const API_REFERENCES = new Map(
    Object.entries(referenceFiles)
        .map(([path, reference]) => /** @type {[string, ApiReference]} */ ([stemOf(path), reference]))
        .sort(([a], [b]) => (a < b ? -1 : 1)),
);

/**
 * @param {Map<string, unknown>} generated
 * @returns {boolean} whether `generated` holds exactly one entry per device
 */
function namesEveryDevice(generated) {
    return generated.size === DEVICE_IDS.length && DEVICE_IDS.every((id) => generated.has(id));
}

if (DEVICE_IDS.length === 0 || !namesEveryDevice(GENERATED_DEFINITIONS) || !namesEveryDevice(API_REFERENCES)) {
    throw new Error("generated definitions missing or stale: run npm run build:site");
}
