// The JS reader of the one MICROPYPATH definition, scripts/micropypath.toml: its twin layout, and a device's own built
// site in place of frozen_modules. Pure, no Node built-ins: tsconfig.json checks it as browser code, and the Node
// frame (tests_js/_twin_process.js) reads the file.

export const LAYOUT_FILE = "scripts/micropypath.toml";
const TWIN_LINE = /^twin = "(?<path>[^"]+)"$/mu;
const SITE_ENTRY = "frozen_modules";

/**
 * The twin layout `text` (the content of `file`) states, or an error naming `file` when no such line is there.
 * @param {string} text
 * @param {string} file
 * @returns {string}
 */
export function twinLayout(text, file) {
    const layout = TWIN_LINE.exec(text)?.groups?.path;
    if (layout === undefined) {
        throw new Error(`${file} has no twin = "..." line`);
    }
    return layout;
}

/**
 * `layout` with its frozen_modules entry swapped for `site`, so a twin boots that device's site and never the unit
 * tier's shared copy; a layout without the entry is refused.
 * @param {string} layout
 * @param {string} site
 * @returns {string}
 */
export function withSite(layout, site) {
    const entries = layout.split(":");
    const at = entries.indexOf(SITE_ENTRY);
    if (at < 0) {
        throw new Error(`MICROPYPATH layout ${layout} has no ${SITE_ENTRY} entry to put the site in`);
    }
    entries[at] = site;
    return entries.join(":");
}
