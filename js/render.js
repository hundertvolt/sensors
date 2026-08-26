/**
 * Section controller - the mechanics half of the visual/mechanics split. Builds no DOM
 * itself; see SPECIFICATION.md Part H.3 for the full layer/contract definition this file follows.
 */

import { formatFieldValue } from "./field-format.js";
import { pollManager, startPolling } from "./poll-manager.js";
import { buildErrcountGroup, buildFieldGroupCard, buildSectionShell } from "./templates.js";

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
        if (rawInputValue === "") {
            return undefined;
        }
        const num = Number(rawInputValue);
        // Non-numeric text must not silently become 0: JSON.stringify(NaN) is "null", and a
        // naive Number(null) === 0 server-side would make garbage input look like a deliberate,
        // possibly in-range "0" instead of failing validation. Send the raw string through
        // instead, so the backend's own Number(value) recreates the same NaN and rejects it.
        return Number.isFinite(num) ? num : rawInputValue;
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
 * A GET's non-ok/empty response, worded using the server's own shaped-error `descr` when present
 * (SPECIFICATION.md Part A.5's `_ERROR_SHAPES`/`_shaped_error_handler` - every 400/404/405/413/500
 * carries one) rather than a bare status code.
 * @param {{ok: boolean, status: number, body: unknown}} response
 * @param {string} url
 * @returns {string}
 */
function describeGetFailure(response, url) {
    const body = /** @type {{descr?: string} | null} */ (response.body);
    if (body?.descr) {
        return `GET ${url} failed: ${body.descr}`;
    }
    if (response.body === null) {
        return `GET ${url} returned an empty body`;
    }
    return `GET ${url} failed: HTTP ${response.status}`;
}

/**
 * Reads whatever the visitor entered/toggled in `card`'s controls back into a plain PUT body,
 * keyed off the same `data-field-key`/`data-sub-field-key` hooks `js/templates.js` sets. A toggle
 * or enum field is sparse-omitted (like every number/string field already is) when it still
 * matches `currentValues` and isn't `dispatch`-marked - see definitions.js's own comment on
 * `FieldDef.dispatch`.
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
        if (field.kind === "toggle") {
            const button = card.querySelector(`[data-field-key="${field.key}"]`);
            if (button instanceof HTMLElement) {
                const value = button.dataset.value === "true";
                if (field.dispatch || value !== Boolean(currentValues[field.key])) {
                    body[field.key] = value;
                }
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
                    // Same NaN -> null -> 0 gap as readInputValue() above; every real subField
                    // today is numeric (e.g. lightCmdLED's r/g/b/t), so this doesn't yet need
                    // readInputValue()'s own per-kind dispatch.
                    const num = Number(input.value);
                    sub[key] = Number.isFinite(num) ? num : input.value;
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
        const value = readInputValue(control.value, field);
        if (field.kind === "enum" && !field.dispatch && value === currentValues[field.key]) {
            continue; // dropdown still at its current selection - nothing changed for this field
        }
        body[field.key] = value;
    }
    return body;
}

/** Worst-first severity order for one card's overall status; see SPECIFICATION.md Part H.3.
 * @type {Record<string, number>}
 */
const STATUS_SEVERITY = { Invalid: 0, Failed: 1, Valid: 2, Unchanged: 3 };

/**
 * A submitted-but-unanswered field is treated as Failed, not silently omitted (SPECIFICATION.md
 * Part H.6 - a known real server-side gap where a settings group's post-write
 * hook raising drops that group's fields from `result` entirely, with no other signal).
 * @param {Record<string, unknown>} submitted
 * @param {Record<string, string>} received
 * @returns {Record<string, string>}
 */
function reconcileResults(submitted, received) {
    const reconciled = { ...received };
    for (const key of Object.keys(submitted)) {
        reconciled[key] ??= "Failed";
    }
    return reconciled;
}

/**
 * Sets the card's `data-apply-status` to the worst of `results`, each individual field's own box
 * to its own result (legacy per-field granularity, kept alongside the newer accent-stripe
 * presentation - SPECIFICATION.md Part H.3), and fills in the outcome text. Only ever writes the
 * semantic status value - `html/style.css` alone decides what each status looks like.
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
    for (const [key, status] of Object.entries(results)) {
        const fieldEl = card.querySelector(`[data-field-wrapper-key="${key}"]`);
        if (fieldEl instanceof HTMLElement) {
            fieldEl.dataset.applyStatus = status.toLowerCase();
        }
    }
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
        const groupBody = collectGroupBody(card, group, currentValues);
        if (Object.keys(groupBody).length === 0) {
            // Every field kind is now sparse-omitted when left untouched (matching value for a
            // toggle/enum, blank for a number/string/composite) - only a `dispatch`-marked field
            // (e.g. SystemCmd, ResetErrors) always resubmits regardless. Skip the round trip
            // entirely rather than PUTing an empty body and letting applyResultStyling()'s
            // empty-result-means-success fallback show a misleading "Valid" for a request that
            // changed nothing.
            if (resultEl) {
                resultEl.textContent = "Nothing to submit - no fields were changed.";
            }
            return;
        }
        // /sensors is the one endpoint whose PUT body nests fields under the sensor's own
        // group key (`{"SCD30": {...}}`) - every other writable section's body is already flat.
        const body = section.key === "sensors" ? { [group.key]: groupBody } : groupBody;
        button.disabled = true;
        try {
            // No decimal-point forcing needed for a field.float-marked field's whole-number value:
            // the real backend now accepts a JSON int for a float-typed field too, coerced
            // (config_manager.py's coerce_numeric(), SPECIFICATION.md Part A.8) - JSON.stringify()
            // is sufficient on its own.
            const response = await pollManager.request(putPath, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const envelope = /** @type {{res?: string, descr?: string, result?: Record<string, unknown>} | null} */ (response.body);
            // Real backend PUT failures (SPECIFICATION.md Part A.8/A.5): a malformed body is a
            // clean HTTP 200 with res:"ERR" (never a shaped HTTP error), while a route-level
            // failure (400/404/405/413/500) is a non-2xx status carrying the same shaped envelope
            // - either one means the request as a whole was rejected, so per-field results (if
            // any survived) can't be trusted as a real per-field breakdown.
            if (!response.ok || envelope === null || envelope.res === "ERR") {
                throw new Error(envelope?.descr ?? `HTTP ${response.status}`);
            }
            const rawResult =
                section.key === "sensors"
                    ? /** @type {Record<string, string> | undefined} */ (envelope.result?.[group.key])
                    : /** @type {Record<string, string> | undefined} */ (envelope.result);
            // /status's PUT (SPECIFICATION.md Part A.8's _put_status()) never returns a per-field
            // result at all, for any of its submit groups - unlike every other writable endpoint,
            // there's no server-side gap for reconcileResults()'s "submitted but missing = Failed"
            // heuristic to guard against here, and applying it anyway would mark every successful
            // submission Failed. A non-2xx/res:"ERR" response already threw above, so reaching this
            // line at all means the call fully succeeded - mark every submitted field Valid
            // directly, the same way the whole-request-failure catch block below marks every
            // submitted field Failed on the opposite outcome.
            const flatResult =
                section.key === "status"
                    ? Object.fromEntries(Object.keys(groupBody).map((key) => [key, "Valid"]))
                    : reconcileResults(groupBody, rawResult ?? {});
            applyResultStyling(card, flatResult, envelope.descr ?? "Done");
            // Keeps collectGroupBody()'s own unchanged-detection correct for a second Apply click
            // later in the same page load, without waiting on onApplied()'s slower GET round trip:
            // a field the server actually stored (Valid or Unchanged, never Failed/Invalid) becomes
            // the new "current" baseline immediately.
            for (const [key, value] of Object.entries(groupBody)) {
                if (flatResult[key] === "Valid" || flatResult[key] === "Unchanged") {
                    currentValues[key] = value;
                }
            }
            onApplied();
        } catch (error) {
            if (resultEl) {
                resultEl.textContent = `Request failed: ${String(error)}`;
            }
            // `card` is a const DOM reference, never reassigned - no real race despite the prior
            // await (this button's own `disabled` guard also rules out a concurrent re-entry).
            // eslint-disable-next-line require-atomic-updates
            card.dataset.applyStatus = "failed";
            // The request never got far enough for a per-field breakdown, so every field that was
            // actually submitted this round shows the same "internal or communication error"
            // status individually too, not just the card border (legacy's own PUT failure handler
            // never colored anything at all - console.error only; this is a deliberate improvement).
            for (const key of Object.keys(groupBody)) {
                const fieldEl = card.querySelector(`[data-field-wrapper-key="${key}"]`);
                if (fieldEl instanceof HTMLElement) {
                    fieldEl.dataset.applyStatus = "failed";
                }
            }
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
    const { grid, errorBanner } = buildSectionShell(section, mainEl);

    /** @param {Record<string, unknown>} data */
    function paint(data) {
        for (const group of section.groups) {
            if ("kind" in group && group.kind === "errcount") {
                const errcountGroup = /** @type {import("./definitions.js").ErrcountGroup} */ (group);
                const errcount = /** @type {Record<string, {counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}>} */ (data.errcount ?? {});
                const existing = grid.querySelector(`[data-group-key="${group.key}"]`);
                const rendered = buildErrcountGroup(errcountGroup, errcount);
                if (existing) {
                    // A live poll (e.g. wozi.json/dev.json's "status" section, pollGroup "live")
                    // rebuilds this card from scratch every tick - without restoring "Show
                    // flagged"/"Show all" here, a visitor's expand choice would silently collapse
                    // back to the default rollup mid-read, every few seconds.
                    const prevModuleList = existing.querySelector(".errcount-module-list");
                    const wasExpanded = prevModuleList instanceof HTMLElement && !prevModuleList.classList.contains("hidden");
                    const wasShowingAll = wasExpanded && [...prevModuleList.children].every((el) => el instanceof HTMLElement && !el.classList.contains("hidden"));
                    existing.replaceWith(rendered);
                    if (wasExpanded) {
                        // Re-clicking the real button (rather than duplicating its hidden-class
                        // toggling logic here) keeps this in lockstep with buildErrcountGroup()'s own
                        // click handlers if that logic ever changes.
                        const action = wasShowingAll ? "all" : "flagged";
                        /** @type {HTMLButtonElement | null} */ (rendered.querySelector(`[data-errcount-action="${action}"]`))?.click();
                    }
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
    }

    /**
     * Self-healing error visibility (SPECIFICATION.md Part H.4): a failed GET surfaces
     * `errorBanner` without clearing stale data, and self-heals on the next success. Never
     * rejects - the one place that catches every fetch failure for this section.
     */
    async function fetchOnce() {
        try {
            const response = await pollManager.request(section.rest.get);
            if (!response.ok || response.body === null) {
                throw new Error(describeGetFailure(response, section.rest.get));
            }
            const data = /** @type {Record<string, unknown>} */ (response.body);
            if (section.key === "notification") {
                // PauseTime is live data (SPECIFICATION.md Part A.8: it lives under GET /status's
                // "notification" sub-key, not GET /notification's own settings-only response), but
                // the "Pause Notifications" group still needs a current value to show/PUT against -
                // so pull it from /status too rather than inventing a second copy of it here.
                const statusResponse = await pollManager.request("/status");
                if (!statusResponse.ok || statusResponse.body === null) {
                    throw new Error(describeGetFailure(statusResponse, "/status"));
                }
                const statusBody = /** @type {Record<string, unknown> | null} */ (statusResponse.body);
                const statusNotification = /** @type {Record<string, unknown>} */ (statusBody?.notification ?? {});
                data.PauseTime = statusNotification.PauseTime;
            }
            errorBanner.classList.add("hidden");
            paint(data);
        } catch (error) {
            errorBanner.textContent = `Could not refresh ${section.label}: ${String(error)}`;
            errorBanner.classList.remove("hidden");
        }
    }

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
