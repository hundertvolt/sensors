/**
 * Reads a module's constants from its raw source (a Vite `?raw` import), so no constant is exported for a test:
 * "Testing must adapt to fit the code, never vice versa." (owner, 2026-09-26).
 */

/**
 * @param {string} name
 * @returns {string}
 */
function escaped(name) {
    return name.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}

/**
 * A top-level `const NAME = <int>;` (an `export` in front also reads) read as its integer.
 * @param {string} source
 * @param {string} name
 * @returns {number}
 */
export function readIntConst(source, name) {
    const match = new RegExp(`^(?:export )?const ${escaped(name)} = (?<value>-?\\d+);$`, "mu").exec(source);
    if (match?.groups?.value === undefined) {
        throw new Error(`no const ${name} in source`);
    }
    return Number(match.groups.value);
}

/**
 * A top-level `const NAME = {<int>: "<text>", ...};` read as its code-to-text table, never evaluated.
 * @param {string} source
 * @param {string} name
 * @returns {Record<string, string>}
 */
export function readObjectConst(source, name) {
    const match = new RegExp(`^(?:export )?const ${escaped(name)} = \\{(?<body>[^}]*)\\};$`, "mu").exec(source);
    if (match?.groups?.body === undefined) {
        throw new Error(`no const ${name} in source`);
    }
    /** @type {Record<string, string>} */
    const table = {};
    for (const entry of match.groups.body.matchAll(/(?<code>\d+):\s*"(?<text>[^"]*)"/gu)) {
        const { code, text } = /** @type {{code: string, text: string}} */ (entry.groups);
        table[code] = text;
    }
    return table;
}
