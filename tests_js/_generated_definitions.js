/**
 * The one tests_js loader for every device's generated definitions and REST reference (build/generated_src/);
 * throws at import when the tree is missing, names another set than devices/*.toml or predates a TOML's text.
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
const tomlFiles = /** @type {Record<string, string>} */ (import.meta.glob("../devices/*.toml", { query: "?raw", eager: true, import: "default" }));

// The generated tree's files that describe no device: the manifest and the inputs stamp.
const NON_DEVICE_STEMS = new Set(["index", "inputs_stamp"]);

/**
 * @param {string} text
 * @returns {Promise<string>} the sha256 of the text's UTF-8 bytes, as hex (the generator hashes the file's bytes)
 */
async function sha256Hex(text) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

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

/**
 * Why the generated tree predates `tomls` (device -> TOML text), against the generator's stamp
 * (build/generated_src/definitions/inputs_stamp.json, `{"tomls": {<device>: <sha256 hex>}}`); empty when it does not.
 * @param {Map<string, string>} tomls
 * @param {unknown} stamp
 * @returns {Promise<string[]>}
 */
export async function staleAgainst(tomls, stamp) {
    const recorded = typeof stamp === "object" && stamp !== null && "tomls" in stamp ? stamp.tomls : undefined;
    if (typeof recorded !== "object" || recorded === null) {
        return ["no TOML stamp"];
    }
    const hashes = new Map(Object.entries(recorded));
    const actual = await Promise.all([...tomls].map(async ([name, text]) => /** @type {const} */ ([name, await sha256Hex(text)])));
    return [
        ...[...hashes.keys()].filter((name) => !tomls.has(name)).map((name) => `${name}: stamped, but no such TOML`),
        ...actual.filter(([name]) => !hashes.has(name)).map(([name]) => `${name}: no stamp`),
        ...actual.filter(([name, hash]) => hashes.has(name) && hashes.get(name) !== hash).map(([name]) => `${name}: changed since the tree was generated`),
    ];
}

const STALE = await staleAgainst(
    new Map(Object.entries(tomlFiles).map(([path, text]) => /** @type {[string, string]} */ ([stemOf(path), text])).filter(([id]) => DEVICE_IDS.includes(id))),
    Object.entries(definitionFiles).find(([path]) => stemOf(path) === "inputs_stamp")?.[1],
);
if (DEVICE_IDS.length === 0 || !namesEveryDevice(GENERATED_DEFINITIONS) || !namesEveryDevice(API_REFERENCES) || STALE.length > 0) {
    throw new Error(`generated definitions missing or stale: run npm run build:site${STALE.length > 0 ? ` (${STALE.join("; ")})` : ""}`);
}
