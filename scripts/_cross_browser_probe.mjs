// The cross-browser smoke's pure decisions, importable without a browser or a twin: which field of
// a device's generated definitions the smoke edits (SPECIFICATION.md Part H.7, "Cross-browser coverage"),
// and whether a WebDriver reply reports a failure.

// Wide enough that the smoke's probe values never repeat within one device's run.
const MIN_PROBE_SPAN = 64;

/**
 * @typedef {{sectionKey: string, groupKey: string, fieldKey: string, min: number, max: number}} Probe
 * @typedef {{key: string, kind: string, float?: boolean, min?: number, max?: number}} ProbeFieldCandidate
 * @typedef {{key: string, submit?: boolean, fields?: ProbeFieldCandidate[]}} ProbeGroupCandidate
 * @typedef {{device: {id: string}, sections: {key: string, groups: ProbeGroupCandidate[]}[]}} ProbeDefinitions
 */

/**
 * The first integer number field with finite bounds at least MIN_PROBE_SPAN apart in a submit
 * group, in definitions order: a field every engine can edit and read back as exact text.
 * @param {ProbeDefinitions} definitions
 * @returns {Probe}
 */
export function pickProbe(definitions) {
    for (const section of definitions.sections) {
        for (const group of section.groups) {
            if (group.submit !== true) {
                continue;
            }
            for (const field of group.fields ?? []) {
                const { min, max } = field;
                const bounded = typeof min === "number" && typeof max === "number" && Number.isFinite(min) && Number.isFinite(max);
                if (field.kind === "number" && field.float !== true && bounded && max - min >= MIN_PROBE_SPAN) {
                    return { sectionKey: section.key, groupKey: group.key, fieldKey: field.key, min, max };
                }
            }
        }
    }
    throw new Error(`device ${JSON.stringify(definitions.device.id)} has no integer field in a submit group with bounds ${MIN_PROBE_SPAN} or more apart to probe`);
}

/**
 * A WebDriver reply's failure, or null: an HTTP status outside 2xx, or a `value.error` (W3C WebDriver's
 * error shape, which some drivers send with a 200).
 * @param {number} status
 * @param {{value?: unknown}} body
 * @returns {string | null}
 */
export function webDriverFailure(status, body) {
    const { value } = body;
    const error = value && typeof value === "object" && "error" in value ? JSON.stringify(value) : null;
    if (status >= 200 && status < 300 && error === null) {
        return null;
    }
    return `HTTP ${status}${error === null ? "" : `: ${error}`}`;
}
