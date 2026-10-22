/**
 * Section controller - the mechanics half of the visual/mechanics split. Builds no DOM
 * itself; see SPECIFICATION.md Part H.3 for the full layer/contract definition this file follows.
 */

import { FAILED, INVALID, isUnavailable, UNCHANGED, VALID } from "./api-contract.js";
import { isRecord, resolveFieldValue } from "./definitions.js";
import { pollManager, startPolling } from "./poll-manager.js";
import { buildErrcountGroup, buildFieldGroupCard, buildSectionShell, resetControl, updateErrcountGroup, updateFieldGroupValues } from "./templates.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").FieldDef} FieldDef */
/** @typedef {import("./poll-manager.js").Visibility} Visibility */
/** @typedef {import("./shell.js").DeviceClock} DeviceClock */
/** @typedef {import("./templates.js").CardDisplay} CardDisplay */
/** @typedef {{begin: () => void, end: () => void}} ApplyTracker */
/**
 * What the shell hands a section; every member is optional, so a bare call renders an always-visible section.
 * @typedef {{visibility?: Visibility, deviceClock?: DeviceClock, onRecovered?: () => void, applyTracker?: ApplyTracker}} SectionContext
 */
/**
 * @typedef {{
 *   baselines: WeakMap<HTMLElement, Record<string, unknown>>, display: CardDisplay,
 *   refreshAfterApply: () => Promise<void>, isStopped: () => boolean, applyTracker: ApplyTracker | undefined,
 * }} ApplyContext
 */

/** Worst-first severity of the four result words; an unknown word ranks below Invalid.
 * @type {Record<string, number>}
 */
const STATUS_SEVERITY = { [INVALID]: 0, [FAILED]: 1, [VALID]: 2, [UNCHANGED]: 3 };

/**
 * Per main element, the section stopped in this turn: the next section rendered there takes its GET on the wire over,
 * so a switch never resets a connection the device is still answering (the device counts that as a peer reset).
 * @type {WeakMap<HTMLElement, {takenOver: boolean, onTheWire: AbortController}>}
 */
const leftSections = new WeakMap();

const NOTHING_TO_SUBMIT = "Nothing to submit - no fields were changed.";
// Also what a browser that suppresses dialogs shows: its confirm() answers false at once.
const CONFIRMATION_DECLINED = "Not sent - the confirmation was declined.";

/**
 * @param {unknown} error
 * @returns {boolean} true for the rejection an aborted request gives (the section was left, or the page stopped).
 */
function isAbort(error) {
    return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

/**
 * @param {unknown} value
 * @returns {boolean} true for a finite number other than zero.
 */
function isNonZeroNumber(value) {
    return typeof value === "number" && Number.isFinite(value) && value !== 0;
}

/**
 * @param {unknown} word
 * @returns {boolean} true for the two words that mean the device holds the value sent.
 */
function isStoredWord(word) {
    return word === VALID || word === UNCHANGED;
}

/**
 * Sets the card's `data-apply-status` to the worst of `results` and each field's own box to its own result, after
 * clearing the previous Apply's (legacy's per-field granularity, Part H.3), and fills in the outcome text. Writes
 * only the semantic status; `html/style.css` alone decides how each one looks.
 * @param {HTMLElement} card
 * @param {Record<string, unknown>} results
 * @param {string} descr
 */
function applyResultStyling(card, results, descr) {
    clearApplyStatus(card);
    /** @type {unknown} */
    let worst;
    for (const [key, word] of Object.entries(results)) {
        const fieldEl = card.querySelector(`[data-field-wrapper-key="${CSS.escape(key)}"]`);
        if (fieldEl instanceof HTMLElement) {
            fieldEl.dataset.applyStatus = applyStatusOf(word);
        }
        if (worst === undefined || severity(word) < severity(worst)) {
            worst = word;
        }
    }
    if (worst !== undefined) {
        card.dataset.applyStatus = applyStatusOf(worst);
    }
    const resultEl = card.querySelector(".apply-result");
    if (resultEl) {
        const perField = Object.entries(results)
            .map(([key, word]) => `${key}: ${String(word)}`)
            .join(", ");
        resultEl.textContent = perField.length > 0 ? `${descr} — ${perField}` : descr;
    }
}

/**
 * @param {unknown} word
 * @returns {string} the `data-apply-status` a result word shows: the word lower-cased, "failed" for an unknown one.
 */
function applyStatusOf(word) {
    return typeof word === "string" && Object.hasOwn(STATUS_SEVERITY, word) ? word.toLowerCase() : "failed";
}

/**
 * Builds a field-group card via `js/templates.js`, then - if the group is writable - attaches the
 * real (networked) Apply and Clear behavior: collect the visitor's edits, PUT them, style the result.
 * @param {FieldGroup} group
 * @param {number} groupIndex the group's place in its section, which the card's field ids carry
 * @param {Section} section
 * @param {Record<string, unknown>} values
 * @param {ApplyContext} ctx
 * @returns {HTMLElement}
 */
function buildAndWireFieldGroup(group, groupIndex, section, values, ctx) {
    const card = buildFieldGroupCard(group, values, groupIndex, ctx.display);
    ctx.baselines.set(card, values);
    if (!group.submit || section.rest.put === undefined) {
        return card;
    }
    const putPath = section.rest.put;

    const button = /** @type {HTMLButtonElement} */ (card.querySelector(".apply-button"));
    const resultEl = card.querySelector(".apply-result");
    const baseline = () => ctx.baselines.get(card) ?? {};
    const updateWarnings = wireWarnings(card, group, baseline);

    /**
     * PUTs one body, shows its per-field results and resets the controls the result settles, then waits for the
     * section's post-write GET; the shell counts it as a pending Apply the whole time.
     * @param {Record<string, unknown>} groupBody
     */
    async function send(groupBody) {
        ctx.applyTracker?.begin();
        button.disabled = true;
        try {
            const results = await putAndShow(groupBody);
            resetSettledControls(card, group, groupBody, results);
            if (!ctx.isStopped()) {
                await ctx.refreshAfterApply();
            }
            resetToBaseline(card, group, groupBody, results, baseline());
            updateWarnings();
        } finally {
            button.disabled = false;
            ctx.applyTracker?.end();
        }
    }

    /**
     * @param {Record<string, unknown>} groupBody
     * @returns {Promise<Record<string, unknown>>} each submitted key's result word
     */
    async function putAndShow(groupBody) {
        // /sensors is the one endpoint whose PUT body nests fields under the sensor's own
        // group key (`{"SCD30": {...}}`) - every other writable section's body is already flat.
        const body = section.key === "sensors" ? { [group.key]: groupBody } : groupBody;
        try {
            // No decimal-point forcing: the backend accepts a JSON int for a float-typed field and coerces it
            // (SPECIFICATION.md Part A.8), so JSON.stringify() is enough.
            const response = await pollManager.request(putPath, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const envelope = /** @type {{res?: string, descr?: string, result?: Record<string, unknown>} | null} */ (response.body);
            // Real backend PUT failures (SPECIFICATION.md C.5.3): a malformed body is a clean 200 with
            // res:"ERR", a route-level failure a non-2xx carrying the same envelope. Either way
            // the request was rejected, so surviving per-field results cannot be trusted.
            if (!response.ok || envelope === null || envelope.res === "ERR") {
                throw new Error(envelope?.descr ?? `HTTP ${response.status}`);
            }
            const rawResult = section.key === "sensors" ? envelope.result?.[group.key] : envelope.result;
            const results = typeof rawResult === "string"
                ? Object.fromEntries(Object.keys(groupBody).map((key) => [key, rawResult]))
                : reconcileResults(groupBody, isRecord(rawResult) ? rawResult : {});
            applyResultStyling(card, results, envelope.descr ?? "Done");
            return results;
        } catch (error) {
            clearApplyStatus(card);
            if (resultEl) {
                resultEl.textContent = `Request failed: ${String(error)}`;
            }
            card.dataset.applyStatus = "failed";
            // No per-field breakdown came back, so every submitted field shows Failed (SPECIFICATION.md Part H.4).
            for (const key of Object.keys(groupBody)) {
                const fieldEl = card.querySelector(`[data-field-wrapper-key="${CSS.escape(key)}"]`);
                if (fieldEl instanceof HTMLElement) {
                    fieldEl.dataset.applyStatus = "failed";
                }
            }
            return Object.fromEntries(Object.keys(groupBody).map((key) => [key, FAILED]));
        }
    }

    button.addEventListener("click", async () => {
        button.disabled = true;
        // Fresh baselines first: another client may have changed a value this page still shows.
        if (!ctx.isStopped()) {
            await ctx.refreshAfterApply();
        }
        const groupBody = collectGroupBody(card, group, baseline());
        if (Object.keys(groupBody).length === 0) {
            // Nothing changed: skip the round trip rather than PUT an empty body.
            if (resultEl) {
                resultEl.textContent = NOTHING_TO_SUBMIT;
            }
            button.disabled = false;
            return;
        }
        if (!confirmEach(group, groupBody)) {
            if (resultEl) {
                resultEl.textContent = CONFIRMATION_DECLINED;
            }
            button.disabled = false;
            return;
        }
        await send(groupBody);
    });

    for (const clear of card.querySelectorAll("[data-clear-for]")) {
        const key = clear.closest("[data-field-wrapper-key]")?.getAttribute("data-field-wrapper-key");
        const field = group.fields.find((candidate) => candidate.key === key);
        if (field === undefined) {
            continue; // unreachable - narrows the type for tsc: templates.js puts every Clear inside its field's box
        }
        clear.addEventListener("click", async () => {
            // A Clear is its own one-key request, never merged with the card's body nor sent beside another.
            if (button.disabled) {
                return;
            }
            if (!window.confirm(`Clear ${field.label}?`)) {
                if (resultEl) {
                    resultEl.textContent = CONFIRMATION_DECLINED;
                }
                return;
            }
            await send({ [field.key]: "" });
        });
    }
    return card;
}

/**
 * @param {HTMLElement} card
 */
function clearApplyStatus(card) {
    delete card.dataset.applyStatus;
    for (const fieldEl of card.querySelectorAll("[data-field-wrapper-key]")) {
        if (fieldEl instanceof HTMLElement) {
            delete fieldEl.dataset.applyStatus;
        }
    }
}

/**
 * Reads the card's controls into a sparse PUT body: a number/string input is sent whenever non-empty, a composite
 * when any sub-input is, an enum/toggle when it differs from its resolveFieldValue() baseline; a dispatch toggle
 * only when On, a dispatch enum when an option is chosen, an always-executed toggle whenever it is set.
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} currentValues
 * @returns {Record<string, unknown>}
 */
function collectGroupBody(card, group, currentValues) {
    /** @type {Record<string, unknown>} */
    const body = {};
    for (const field of group.fields) {
        if (field.kind === "readonly") {
            continue;
        }
        const control = card.querySelector(`[data-field-key="${CSS.escape(field.key)}"]`);
        const value = field.kind === "toggle" || field.kind === "composite" ? readCompound(control, field, currentValues) : readTextOrSelect(control, field, currentValues);
        if (value !== undefined) {
            body[field.key] = value;
        }
    }
    return body;
}

/**
 * Asks the browser's confirmation for every key of `groupBody` whose field carries `confirm`: an enum names the
 * chosen option, a toggle the group's submit label.
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} groupBody
 * @returns {boolean} true when nothing needed asking or every question was answered OK
 */
function confirmEach(group, groupBody) {
    for (const [key, value] of Object.entries(groupBody)) {
        const field = group.fields.find((candidate) => candidate.key === key);
        if (field?.confirm !== true) {
            continue;
        }
        const what = field.kind === "enum"
            ? ((field.options ?? []).find((option) => option.value === value)?.label ?? String(value))
            : (group.submitLabel ?? field.label);
        if (!window.confirm(`${what}?`)) {
            return false;
        }
    }
    return true;
}

/**
 * A GET's non-ok, empty or non-object response, worded with the server's shaped-error `descr` when present (every
 * 400/404/405/413/500 envelope carries one, SPECIFICATION.md C.5.3) rather than a bare status code.
 * @param {{ok: boolean, status: number, body: unknown}} response
 * @param {string} url
 * @returns {string}
 */
function describeGetFailure(response, url) {
    if (!response.ok) {
        const descr = isRecord(response.body) ? response.body.descr : undefined;
        return typeof descr === "string" && descr !== "" ? `GET ${url} failed: ${descr}` : `GET ${url} failed: HTTP ${response.status}`;
    }
    return response.body === null ? `GET ${url} returned an empty body` : `GET ${url} returned no JSON object`;
}

/**
 * @param {HTMLElement} card
 * @param {FieldDef} field
 * @returns {HTMLElement | null} the field's `[data-field-wrapper-key]` box
 */
function fieldBoxOf(card, field) {
    const box = card.querySelector(`[data-field-wrapper-key="${CSS.escape(field.key)}"]`);
    return box instanceof HTMLElement ? box : null;
}

/**
 * A field group's source in its section's GET body: its own entry for measurements, sensors and status
 * (the maintenance group's is the sensors map), the whole body for every other section.
 * @param {Section} section
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} data
 * @returns {Record<string, unknown>}
 */
function groupSourceFrom(section, group, data) {
    if (section.key === "measurements" || section.key === "sensors" || section.key === "status") {
        return /** @type {Record<string, unknown>} */ (data[group.key] ?? {});
    }
    return data;
}

/**
 * A field group's values: its source (groupSourceFrom(), never flattened - a `path` field walks it), with each
 * `statusPath` field's key set to the walk of that path over the /status body.
 * @param {Section} section
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} data
 * @param {unknown} statusBody
 * @returns {Record<string, unknown>}
 */
function groupValuesFrom(section, group, data, statusBody) {
    const source = groupSourceFrom(section, group, data);
    const statusFields = group.fields.filter((field) => field.statusPath !== undefined);
    if (statusFields.length === 0) {
        return source;
    }
    const values = { ...source };
    const statusValues = isRecord(statusBody) ? statusBody : {};
    for (const field of statusFields) {
        values[field.key] = resolveFieldValue({ ...field, path: field.statusPath ?? [] }, statusValues);
    }
    return values;
}

/**
 * @param {unknown} root
 * @param {string[]} path
 * @returns {boolean} true when walking `path` from `root` meets the degraded-source marker before its leaf.
 */
function meetsUnavailable(root, path) {
    let cursor = root;
    for (const step of path) {
        if (isUnavailable(cursor)) {
            return true;
        }
        if (!isRecord(cursor)) {
            return false;
        }
        cursor = cursor[step];
    }
    return false;
}

/**
 * A number only for plain decimal text; anything else is sent raw for the device to reject.
 * @param {string} text
 * @returns {number | string}
 */
function parseNumberInput(text) {
    const trimmed = text.trim();
    return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/u.test(trimmed) ? Number(trimmed) : text;
}

/**
 * A toggle's or a composite's contribution to the PUT body, per collectGroupBody()'s rules.
 * @param {Element | null} control
 * @param {FieldDef} field
 * @param {Record<string, unknown>} currentValues
 * @returns {unknown} the value to send; undefined when the field is left out
 */
function readCompound(control, field, currentValues) {
    if (!(control instanceof HTMLElement)) {
        return undefined;
    }
    if (field.kind === "toggle") {
        const state = control.dataset.value;
        if (state !== "true" && state !== "false") {
            return undefined; // unset: an always-executed toggle nobody has set
        }
        const value = state === "true";
        if (field.dispatch === true) {
            return value ? true : undefined;
        }
        return field.alwaysExecuted === true || value !== Boolean(resolveFieldValue(field, currentValues)) ? value : undefined;
    }
    /** @type {Record<string, unknown>} */
    const sub = {};
    for (const input of control.querySelectorAll("input")) {
        const key = input.dataset.subFieldKey;
        if (key !== undefined && input.value !== "") {
            sub[key] = parseNumberInput(input.value);
        }
    }
    return Object.keys(sub).length > 0 ? sub : undefined;
}

/**
 * @param {string} rawInputValue
 * @param {FieldDef} field
 * @returns {unknown}
 */
function readInputValue(rawInputValue, field) {
    if (field.kind === "number") {
        // Text that is not a plain decimal is sent as typed: the device rejects it, so garbage never becomes a
        // plausible number.
        return rawInputValue === "" ? undefined : parseNumberInput(rawInputValue);
    }
    if (field.kind === "enum") {
        // A <select>'s own .value is always a string (DOM behavior), even when the option's real
        // value is numeric (e.g. BMP3XX's PresOvers) - look the matching option back up so the
        // submitted PUT body carries the same type definitions.json declared, not a stringified one.
        const match = (field.options ?? []).find((option) => String(option.value) === rawInputValue);
        return match ? match.value : rawInputValue;
    }
    return rawInputValue;
}

/**
 * A number/string input's or a select's contribution to the PUT body, per collectGroupBody()'s rules.
 * @param {Element | null} control
 * @param {FieldDef} field
 * @param {Record<string, unknown>} currentValues
 * @returns {unknown} the value to send; undefined when the field is left out
 */
function readTextOrSelect(control, field, currentValues) {
    if (!(control instanceof HTMLInputElement) && !(control instanceof HTMLSelectElement)) {
        return undefined;
    }
    if (control.value === "") {
        return undefined; // sparse PUT: an untouched input is omitted, not sent as empty
    }
    const value = readInputValue(control.value, field);
    if (field.kind === "enum" && field.dispatch !== true && value === resolveFieldValue(field, currentValues)) {
        return undefined; // dropdown still at its current selection - nothing changed for this field
    }
    return value;
}

/**
 * Defensive only: the server answers every submitted key (SPECIFICATION.md A.8); a missing one is shown Failed
 * rather than dropped.
 * @param {Record<string, unknown>} submitted
 * @param {Record<string, unknown>} received
 * @returns {Record<string, unknown>}
 */
function reconcileResults(submitted, received) {
    const reconciled = { ...received };
    for (const key of Object.keys(submitted)) {
        reconciled[key] ??= FAILED;
    }
    return reconciled;
}

/**
 * After an Apply's results: every dispatch toggle or enum of the group back to Off or its placeholder, every
 * always-executed toggle to unset, and each submitted text or composite the device stored cleared.
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} groupBody
 * @param {Record<string, unknown>} results
 */
function resetSettledControls(card, group, groupBody, results) {
    for (const field of group.fields) {
        const box = fieldBoxOf(card, field);
        if (box === null) {
            continue;
        }
        if (field.dispatch === true && (field.kind === "toggle" || field.kind === "enum")) {
            resetControl(box, field, field.kind === "toggle" ? false : undefined);
        } else if (field.alwaysExecuted === true && field.kind === "toggle") {
            resetControl(box, field, undefined);
        } else if (field.kind !== "toggle" && field.kind !== "enum" && Object.hasOwn(groupBody, field.key) && isStoredWord(results[field.key])) {
            resetControl(box, field, undefined);
        }
    }
}

/**
 * After the post-write GET: each submitted plain toggle or enum the device stored shows the value it now reports.
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} groupBody
 * @param {Record<string, unknown>} results
 * @param {Record<string, unknown>} currentValues
 */
function resetToBaseline(card, group, groupBody, results, currentValues) {
    for (const field of group.fields) {
        const plain = (field.kind === "toggle" || field.kind === "enum") && field.dispatch !== true && field.alwaysExecuted !== true;
        const box = fieldBoxOf(card, field);
        if (plain && box !== null && Object.hasOwn(groupBody, field.key) && isStoredWord(results[field.key])) {
            resetControl(box, field, resolveFieldValue(field, currentValues));
        }
    }
}

/**
 * @param {unknown} word
 * @returns {number} the word's STATUS_SEVERITY rank; -1, the worst, for an unknown word.
 */
function severity(word) {
    return typeof word === "string" && Object.hasOwn(STATUS_SEVERITY, word) ? (STATUS_SEVERITY[word] ?? -1) : -1;
}

/**
 * Shows each `ignoredWhenSet` field's warning while its input holds text and its sibling's effective value - the
 * sibling's typed number, else its baseline - is a non-zero number.
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 * @param {() => Record<string, unknown>} baseline
 * @returns {() => void} re-evaluates every warning of the card
 */
function wireWarnings(card, group, baseline) {
    /** @type {(() => void)[]} */
    const updates = [];
    for (const field of group.fields) {
        const sibling = group.fields.find((candidate) => candidate.key === field.ignoredWhenSet);
        const input = card.querySelector(`input[data-field-key="${CSS.escape(field.key)}"]`);
        const warning = fieldBoxOf(card, field)?.querySelector(".field-warning");
        if (sibling === undefined || !(input instanceof HTMLInputElement) || !(warning instanceof HTMLElement)) {
            continue;
        }
        const siblingInput = card.querySelector(`input[data-field-key="${CSS.escape(sibling.key)}"]`);
        const update = () => {
            const typed = siblingInput instanceof HTMLInputElement && siblingInput.value !== "" ? parseNumberInput(siblingInput.value) : undefined;
            const siblingValue = typeof typed === "number" && Number.isFinite(typed) ? typed : resolveFieldValue(sibling, baseline());
            warning.dataset.shown = String(input.value !== "" && isNonZeroNumber(siblingValue));
        };
        input.addEventListener("input", update);
        siblingInput?.addEventListener("input", update);
        updates.push(update);
    }
    return () => {
        for (const update of updates) {
            update();
        }
    };
}

/**
 * Hides a banner; its text stays, the next showBanner() replaces it.
 * @param {HTMLElement} el
 */
export function hideBanner(el) {
    el.dataset.shown = "false";
}

/**
 * Renders `section` into `mainEl` once and keeps it current in place: every section's GET runs through one poll
 * loop (a non-live one stops after its first success), and a failed GET shows the banner until a later one succeeds.
 * @param {SiteDefinitions} defs
 * @param {Section} section
 * @param {HTMLElement} mainEl
 * @param {SectionContext} [context]
 * @returns {() => void} stop, before a switch: drops the queued GETs; the GET on the wire runs to its end, discarded,
 * when another section is rendered into `mainEl` in the same turn, else (the page stops) it is aborted, with any it took over.
 */
export function renderSection(defs, section, mainEl, context = {}) {
    const left = leftSections.get(mainEl);
    leftSections.delete(mainEl);
    const { grid, errorBanner } = buildSectionShell(section, mainEl);
    const queued = new AbortController();
    const onTheWire = new AbortController();
    if (left !== undefined) {
        left.takenOver = true;
        onTheWire.signal.addEventListener("abort", () => left.onTheWire.abort(), { once: true });
    }
    /** @type {WeakMap<HTMLElement, Record<string, unknown>>} */
    const baselines = new WeakMap();
    const needsStatus = section.rest.get !== "/status"
        && section.groups.some((group) => ("kind" in group && group.kind === "errcount") || ("fields" in group && group.fields.some((field) => field.statusPath !== undefined)));
    let stopped = false;
    let failing = false;
    const isStopped = () => stopped;

    /**
     * @param {string} url
     * @returns {Promise<Record<string, unknown>>}
     */
    async function getBody(url) {
        const response = await pollManager.request(url, undefined, undefined, onTheWire.signal, queued.signal);
        if (!response.ok || !isRecord(response.body)) {
            throw new Error(describeGetFailure(response, url));
        }
        return response.body;
    }

    /** One refresh: the section's GET, then /status when a group reads it; throws on any failure. */
    async function fetchOnce() {
        const data = await getBody(section.rest.get);
        let statusBody = section.rest.get === "/status" ? data : undefined;
        if (needsStatus) {
            statusBody = await getBody("/status");
        }
        if (stopped) {
            return; // a left section's GET that ran to its end: discarded, the device clock included
        }
        if (statusBody !== undefined) {
            context.deviceClock?.observe(statusBody);
        }
        paint(data, statusBody);
    }

    /** @param {unknown} error */
    function onError(error) {
        if (stopped || isAbort(error)) {
            return;
        }
        showBanner(errorBanner, `Could not refresh ${section.label}: ${String(error)}`);
        if (!failing) {
            failing = true;
            console.error(`Could not refresh ${section.label}:`, error);
        }
    }

    function onSuccess() {
        if (stopped) {
            return;
        }
        hideBanner(errorBanner);
        if (failing) {
            failing = false;
            context.onRecovered?.();
        }
    }

    /** The post-write GET: never rejects, a failure taking the section's own banner path. */
    function refreshAfterApply() {
        return fetchOnce().then(onSuccess, onError);
    }

    /**
     * @param {Record<string, unknown>} data
     * @param {unknown} statusBody
     */
    function paint(data, statusBody) {
        for (const [groupIndex, group] of section.groups.entries()) {
            const existing = grid.querySelector(`[data-group-key="${CSS.escape(group.key)}"]`);
            if ("kind" in group && group.kind === "errcount") {
                const errcount = isRecord(statusBody) && isRecord(statusBody.errcount) ? statusBody.errcount : null;
                if (existing instanceof HTMLElement) {
                    updateErrcountGroup(existing, group, errcount);
                } else {
                    grid.appendChild(buildErrcountGroup(group, errcount));
                }
                continue;
            }
            const fieldGroup = /** @type {FieldGroup} */ (group);
            const source = groupSourceFrom(section, fieldGroup, data);
            const values = groupValuesFrom(section, fieldGroup, data, statusBody);
            const sourceUnavailable = isUnavailable(source);
            /** @type {CardDisplay} */
            const display = {
                deviceNowS: context.deviceClock?.nowS() ?? null,
                defaultDecimals: defs.defaultDecimals,
                isUnavailable: (field) => sourceUnavailable || (field.statusPath === undefined
                    ? meetsUnavailable(source, field.path ?? [])
                    : meetsUnavailable(statusBody, field.statusPath)),
            };
            /** @type {HTMLElement} */
            let card;
            if (existing instanceof HTMLElement) {
                card = existing;
                baselines.set(card, values);
                updateFieldGroupValues(card, fieldGroup, values, display);
            } else {
                card = buildAndWireFieldGroup(fieldGroup, groupIndex, section, values, {
                    baselines, display, refreshAfterApply, isStopped, applyTracker: context.applyTracker,
                });
                grid.appendChild(card);
            }
            if (sourceUnavailable) {
                card.dataset.sourceState = "unavailable";
            } else {
                delete card.dataset.sourceState;
            }
        }
    }

    const stopLoop = startPolling(
        async () => {
            await fetchOnce();
            onSuccess();
        },
        section.pollIntervalMs ?? defs.defaultPollIntervalMs,
        {
            ...(context.visibility === undefined ? {} : { visibility: context.visibility }),
            onError,
            stopAfterSuccess: section.pollGroup !== "live",
        },
    );
    return () => {
        if (stopped) {
            return;
        }
        stopped = true;
        queued.abort();
        stopLoop();
        const handover = { takenOver: false, onTheWire };
        leftSections.set(mainEl, handover);
        queueMicrotask(() => {
            if (leftSections.get(mainEl) === handover) {
                leftSections.delete(mainEl);
            }
            if (!handover.takenOver) {
                onTheWire.abort();
            }
        });
    };
}

/**
 * Shows `message` in a banner.
 * @param {HTMLElement} el
 * @param {string} message
 */
export function showBanner(el, message) {
    el.textContent = message;
    el.dataset.shown = "true";
}
