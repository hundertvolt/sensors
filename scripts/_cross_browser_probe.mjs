// The cross-browser smoke's pure decisions, importable without a browser or a twin: which field of a device's
// generated definitions the smoke edits (SPECIFICATION.md Part H.7, "Cross-browser coverage"), whether a WebDriver
// reply reports a failure, and the run's verdict over the engines it found and the checks it ran.

// Wide enough that the smoke's probe values never repeat within one device's run.
const MIN_PROBE_SPAN = 64;

/**
 * @typedef {{sectionKey: string, groupKey: string, fieldKey: string, min: number, max: number}} Probe
 * @typedef {{key: string, kind: string, float?: boolean, min?: number, max?: number}} ProbeFieldCandidate
 * @typedef {{key: string, submit?: boolean, fields?: ProbeFieldCandidate[]}} ProbeGroupCandidate
 * @typedef {{device: {id: string}, sections: {key: string, groups: ProbeGroupCandidate[]}[]}} ProbeDefinitions
 * @typedef {{label: string, ok: boolean, detail?: string}} CheckResult
 * @typedef {{name: string, missing: string[]}} EngineAvailability
 * @typedef {{results: CheckResult[], skips: {label: string, detail: string}[], passed: number, ran: number, skipped: number}} EngineVerdict
 */

/**
 * The run's verdict: every engine lacking a binary fails, naming it, under requireAllEngines (CI), and is otherwise a
 * skip the closing line counts; `ran` and `passed` count the results, a required engine's failure among them.
 * @param {EngineAvailability[]} available each engine with the binaries it lacks (none: it ran)
 * @param {CheckResult[]} results the checks the run made
 * @param {{requireAllEngines: boolean}} options
 * @returns {EngineVerdict}
 */
export function engineVerdict(available, results, { requireAllEngines }) {
    const absent = available.filter((engine) => engine.missing.length > 0);
    const notFound = (/** @type {EngineAvailability} */ engine) => `${engine.missing.join(" and ")} not found`;
    const failures = requireAllEngines ? absent.map((engine) => ({ label: engine.name, ok: false, detail: `${notFound(engine)} - CI requires every engine (run scripts/setup_cross_browser_toolchain.sh)` })) : [];
    const skips = requireAllEngines ? [] : absent.map((engine) => ({ label: engine.name, detail: `${notFound(engine)} (run scripts/setup_cross_browser_toolchain.sh)` }));
    const all = [...results, ...failures];
    return { results: all, skips, passed: all.filter((result) => result.ok).length, ran: all.length, skipped: skips.length };
}

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
