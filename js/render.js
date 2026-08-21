/**
 * Section controller (WEBSITE_PLAN.md §12): owns everything that talks to the network or
 * validates/submits data - fetching, polling, collecting a group's input values into a PUT body,
 * and turning a PUT response into an apply-status outcome. It builds no DOM itself; every element
 * comes from `js/templates.js`, located afterwards only via the `data-*` attributes/CSS classes
 * documented in WEBSITE_PLAN.md §12's contract table. A purely visual/layout redesign never
 * touches this file.
 */

import { pollManager, startPolling } from "./poll-manager.js";
import { buildErrcountGroup, buildFieldGroupCard, buildSectionShell, formatFieldValue } from "./templates.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").FieldDef} FieldDef */

/**
 * @param {unknown} rawInputValue
 * @param {FieldDef} field
 * @returns {unknown}
 */
function readInputValue(rawInputValue, field) {
    if (field.kind === "number") {
        return rawInputValue === "" ? undefined : Number(rawInputValue);
    }
    if (field.kind === "enum") {
        // A <select>'s own .value is always a string (DOM behavior), even when the option's real
        // value is numeric (e.g. BMP3XX's PressOvers) - look the matching option back up so the
        // submitted PUT body carries the same type definitions.json declared, not a stringified one.
        const match = (field.options ?? []).find((option) => String(option.value) === rawInputValue);
        return match ? match.value : rawInputValue;
    }
    return rawInputValue;
}

/**
 * Reads whatever the visitor entered/toggled in `card`'s controls back into a plain PUT body,
 * keyed off the same `data-field-key`/`data-sub-field-key` hooks `js/templates.js` sets.
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 */
function collectGroupBody(card, group) {
    /** @type {Record<string, unknown>} */
    const body = {};
    for (const field of group.fields) {
        if (field.kind === "readonly") {
            continue;
        }
        if (field.kind === "toggle") {
            const button = card.querySelector(`[data-field-key="${field.key}"]`);
            if (button instanceof HTMLElement) {
                body[field.key] = button.dataset.value === "true";
            }
            continue;
        }
        if (field.kind === "composite") {
            const grid = card.querySelector(`[data-field-key="${field.key}"]`);
            if (!(grid instanceof HTMLElement)) {
                continue;
            }
            /** @type {Record<string, unknown>} */
            const sub = {};
            let anyFilled = false;
            for (const input of grid.querySelectorAll("input")) {
                const key = input.dataset.subFieldKey;
                if (key !== undefined && input.value !== "") {
                    sub[key] = Number(input.value);
                    anyFilled = true;
                }
            }
            if (anyFilled) {
                body[field.key] = sub;
            }
            continue;
        }
        const control = card.querySelector(`[data-field-key="${field.key}"]`);
        if (!(control instanceof HTMLInputElement) && !(control instanceof HTMLSelectElement)) {
            continue;
        }
        if (control.value === "") {
            continue; // sparse PUT: an untouched input is omitted, not sent as empty
        }
        body[field.key] = readInputValue(control.value, field);
    }
    return body;
}

/**
 * Worst-first ordering used to pick one status for the whole card from several field results.
 * Real problems (Invalid/Failed) always win; between the two non-problem outcomes, a genuine
 * Valid change outranks an Unchanged no-op, so e.g. one changed field + one resubmitted-as-is
 * field reads as "valid" (something happened), not "unchanged" (nothing did).
 * @type {Record<string, number>}
 */
const STATUS_SEVERITY = { Invalid: 0, Failed: 1, Valid: 2, Unchanged: 3 };

/**
 * Sets the card's `data-apply-status` to the worst of `results` and fills in the outcome text.
 * Only ever writes the semantic status value - `html/style.css` alone decides what each status
 * looks like (WEBSITE_PLAN.md §12).
 * @param {HTMLElement} card
 * @param {Record<string, string>} results
 * @param {string} descr
 */
function applyResultStyling(card, results, descr) {
    const values = Object.values(results);
    const worst = values.reduce(
        (acc, status) => (((STATUS_SEVERITY[status] ?? 4) < (STATUS_SEVERITY[acc] ?? 4)) ? status : acc),
        "Valid", // e.g. /status's ResetErrors: an empty `result` map on a successful envelope
        // still means the action completed, not that "nothing changed" - default to success.
    );
    card.dataset.applyStatus = worst.toLowerCase();
    const resultEl = card.querySelector(".apply-result");
    if (resultEl) {
        const perField = Object.entries(results)
            .map(([key, status]) => `${key}: ${status}`)
            .join(", ");
        resultEl.textContent = perField.length > 0 ? `${descr} — ${perField}` : descr;
    }
}

/**
 * Builds a field-group card via `js/templates.js`, then - if the group is writable - attaches the
 * real (networked) Apply-button behavior: collect the visitor's edits, PUT them, style the result.
 * @param {FieldGroup} group
 * @param {Section} section
 * @param {Record<string, unknown>} currentValues
 * @param {() => void} onApplied called after a PUT resolves, to refresh current-value captions.
 * @returns {HTMLElement}
 */
function buildAndWireFieldGroup(group, section, currentValues, onApplied) {
    const card = buildFieldGroupCard(group, currentValues);
    if (!group.submit) {
        return card;
    }

    const button = /** @type {HTMLButtonElement} */ (card.querySelector(".apply-button"));
    const resultEl = card.querySelector(".apply-result");
    button.addEventListener("click", async () => {
        const putPath = section.rest.put;
        if (putPath === undefined) {
            return;
        }
        const groupBody = collectGroupBody(card, group);
        // /sensors is the one endpoint whose PUT body nests fields under the sensor's own
        // group key (`{"SCD30": {...}}`) - every other writable section's body is already flat.
        const body = section.key === "sensors" ? { [group.key]: groupBody } : groupBody;
        button.disabled = true;
        try {
            const response = await pollManager.request(putPath, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const envelope = /** @type {{descr?: string, result?: Record<string, unknown>}} */ (response.body ?? {});
            const flatResult =
                section.key === "sensors"
                    ? /** @type {Record<string, string>} */ (envelope.result?.[group.key] ?? {})
                    : /** @type {Record<string, string>} */ (envelope.result ?? {});
            applyResultStyling(card, flatResult, envelope.descr ?? "Done");
            onApplied();
        } catch (error) {
            if (resultEl) {
                resultEl.textContent = `Request failed: ${String(error)}`;
            }
            card.dataset.applyStatus = "failed";
        } finally {
            button.disabled = false;
        }
    });
    return card;
}

/**
 * Renders `section` into `mainEl` and wires live polling if applicable.
 * @param {SiteDefinitions} defs
 * @param {Section} section
 * @param {HTMLElement} mainEl
 * @returns {() => void} stop function - call before switching to another section.
 */
export function renderSection(defs, section, mainEl) {
    const grid = buildSectionShell(section, mainEl);

    /** @param {Record<string, unknown>} data */
    const paint = (data) => {
        for (const group of section.groups) {
            if ("kind" in group && group.kind === "errcount") {
                const errcountGroup = /** @type {import("./definitions.js").ErrcountGroup} */ (group);
                const errcount = /** @type {any} */ (data).errcount ?? {};
                const existing = grid.querySelector(`[data-group-key="${group.key}"]`);
                const rendered = buildErrcountGroup(errcountGroup, errcount);
                rendered.dataset.groupKey = group.key;
                if (existing) {
                    existing.replaceWith(rendered);
                } else {
                    grid.appendChild(rendered);
                }
                continue;
            }
            const fieldGroup = /** @type {FieldGroup} */ (group);
            const groupValues = groupValuesFrom(section, fieldGroup, data);
            const existing = grid.querySelector(`[data-group-key="${fieldGroup.key}"]`);
            if (existing && fieldGroup.submit) {
                // Writable groups only refresh their read-only captions/spans in place, so an
                // in-progress edit in an input the visitor is typing into is never clobbered by a poll.
                for (const field of fieldGroup.fields) {
                    const caption = existing.querySelector(`[data-current-value-for="${field.key}"]`);
                    if (caption) {
                        caption.textContent = `Current value: ${formatFieldValue(field, groupValues[field.key])}`;
                    }
                    const readonlySpan = existing.querySelector(`.field-value[data-field-key="${field.key}"]`);
                    if (readonlySpan) {
                        readonlySpan.textContent = formatFieldValue(field, groupValues[field.key]);
                    }
                }
                continue;
            }
            const rendered = buildAndWireFieldGroup(fieldGroup, section, groupValues, () => void fetchOnce());
            if (existing) {
                existing.replaceWith(rendered);
            } else {
                grid.appendChild(rendered);
            }
        }
    };

    const fetchOnce = async () => {
        const response = await pollManager.request(section.rest.get);
        if (!response.ok || response.body === null) {
            return;
        }
        const data = /** @type {Record<string, unknown>} */ (response.body);
        if (section.key === "notification") {
            // PauseTime is live data (SPECIFICATION.md Part A.8: it lives under GET /status's
            // "notification" sub-key, not GET /notification's own settings-only response), but the
            // "Pause Notifications" group still needs a current value to show/PUT against - so pull
            // it from /status too rather than inventing a second copy of it in the settings endpoint.
            const statusResponse = await pollManager.request("/status");
            const statusNotification = /** @type {any} */ (statusResponse.body)?.notification ?? {};
            data.PauseTime = statusNotification.PauseTime;
        }
        paint(data);
    };

    if (section.pollGroup === "live") {
        const stop = startPolling(fetchOnce, section.pollIntervalMs ?? defs.defaultPollIntervalMs);
        return stop;
    }

    void fetchOnce();
    return () => {};
}

/**
 * Measurements/sensors config are keyed by sensor name one level deep (`{"SCD30": {...}}`);
 * flat settings sections (networking/system/notification) are already flat. Errcount-only
 * groups never reach this helper.
 * @param {Section} section
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} data
 * @returns {Record<string, unknown>}
 */
function groupValuesFrom(section, group, data) {
    if (section.key === "measurements" || section.key === "sensors") {
        return /** @type {Record<string, unknown>} */ (data[group.key] ?? {});
    }
    if (section.key === "status" && group.key === "sensors") {
        // Maintenance data is per-sensor (`{"SGP40": {BackupTS, RestoreTS}}`); flatten one level
        // so field keys can address it directly (e.g. "SGP40_BackupTS"), matching every other
        // group's already-flat field-key convention.
        /** @type {Record<string, unknown>} */
        const flat = {};
        const bySensor = /** @type {Record<string, Record<string, unknown>>} */ (data.sensors ?? {});
        for (const [sensorKey, fields] of Object.entries(bySensor)) {
            for (const [fieldKey, value] of Object.entries(fields)) {
                flat[`${sensorKey}_${fieldKey}`] = value;
            }
        }
        return flat;
    }
    if (section.key === "status") {
        return /** @type {Record<string, unknown>} */ (data[group.key] ?? {});
    }
    return data;
}
