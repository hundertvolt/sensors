/**
 * Generic, definitions-driven section renderer (WEBSITE_PLAN.md §10 session 2). Every section/
 * group/field is built from the fetched definitions.json - there is no per-device branching here,
 * which is the actual proof that "one skeleton/JS, content from definitions file" generalizes.
 */

import { pollManager, startPolling } from "./poll-manager.js";

/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").FieldDef} FieldDef */

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @returns {string}
 */
function formatValue(field, value) {
    if (value === undefined || value === null) {
        return "—";
    }
    if (field.mask === true) {
        return "••••••••";
    }
    if (field.kind === "enum") {
        const match = (field.options ?? []).find((option) => option.value === value);
        return match ? match.label : String(value);
    }
    return String(value);
}

/**
 * @param {FieldDef} field
 * @returns {HTMLElement}
 */
function renderFieldDescription(field) {
    const parts = [];
    if (field.kind === "number" && (field.min !== undefined || field.max !== undefined)) {
        parts.push(`Valid values: ${field.min ?? "–∞"} to ${field.max ?? "∞"}${field.unit ? ` ${field.unit}` : ""}`);
    }
    if (field.kind === "string" && (field.minLength !== undefined || field.maxLength !== undefined)) {
        parts.push(`Length: ${field.minLength ?? 0} to ${field.maxLength ?? "∞"} characters`);
    }
    for (const special of field.specialValues ?? []) {
        parts.push(`${special.value} = ${special.meaning}`);
    }
    if (field.description) {
        parts.push(field.description);
    }
    const p = document.createElement("p");
    p.className = "field-description";
    p.textContent = parts.join(" · ");
    return p;
}

/**
 * @param {FieldDef} field
 * @param {unknown} currentValue
 * @param {boolean} editable
 * @returns {HTMLElement}
 */
function renderField(field, currentValue, editable) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";

    const label = document.createElement("label");
    label.className = "field-label";
    label.htmlFor = `field-${field.key}`;
    label.textContent = field.label;
    if (field.unit) {
        const unitSpan = document.createElement("span");
        unitSpan.className = "field-unit";
        unitSpan.textContent = ` [${field.unit}]`;
        label.appendChild(unitSpan);
    }
    wrapper.appendChild(label);

    if (!editable || field.kind === "readonly") {
        const value = document.createElement("span");
        value.className = "field-value";
        value.dataset.fieldKey = field.key;
        value.textContent = formatValue(field, currentValue);
        wrapper.appendChild(value);
        wrapper.appendChild(renderFieldDescription(field));
        return wrapper;
    }

    if (field.kind === "toggle") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "toggle-button";
        button.id = `field-${field.key}`;
        button.dataset.fieldKey = field.key;
        const initial = Boolean(currentValue);
        button.dataset.value = String(initial);
        button.setAttribute("aria-pressed", String(initial));
        button.textContent = initial ? (field.onLabel ?? "On") : (field.offLabel ?? "Off");
        button.addEventListener("click", () => {
            const next = button.dataset.value !== "true";
            button.dataset.value = String(next);
            button.setAttribute("aria-pressed", String(next));
            button.textContent = next ? (field.onLabel ?? "On") : (field.offLabel ?? "Off");
        });
        wrapper.appendChild(button);
        wrapper.appendChild(renderFieldDescription(field));
        return wrapper;
    }

    if (field.kind === "enum") {
        const select = document.createElement("select");
        select.id = `field-${field.key}`;
        select.dataset.fieldKey = field.key;
        for (const option of field.options ?? []) {
            const optionEl = document.createElement("option");
            optionEl.value = option.value;
            optionEl.textContent = option.label;
            if (option.value === currentValue) {
                optionEl.selected = true;
            }
            select.appendChild(optionEl);
        }
        wrapper.appendChild(select);
        wrapper.appendChild(renderFieldDescription(field));
        return wrapper;
    }

    if (field.kind === "composite") {
        const grid = document.createElement("div");
        grid.className = "composite-fields";
        grid.dataset.fieldKey = field.key;
        for (const subField of field.subFields ?? []) {
            const subWrapper = document.createElement("label");
            const caption = document.createElement("span");
            caption.className = "field-unit";
            caption.textContent = subField.label;
            const input = document.createElement("input");
            input.type = "text";
            input.dataset.subFieldKey = subField.key;
            input.value = "";
            input.placeholder = subField.label;
            subWrapper.appendChild(caption);
            subWrapper.appendChild(input);
            grid.appendChild(subWrapper);
        }
        wrapper.appendChild(grid);
        wrapper.appendChild(renderFieldDescription(field));
        return wrapper;
    }

    // number or string
    const input = document.createElement("input");
    input.type = field.mask === true ? "password" : "text";
    input.id = `field-${field.key}`;
    input.dataset.fieldKey = field.key;
    input.value = "";
    input.placeholder = formatValue(field, currentValue);
    wrapper.appendChild(input);

    const caption = document.createElement("p");
    caption.className = "field-description";
    caption.dataset.currentValueFor = field.key;
    caption.textContent = `Current value: ${formatValue(field, currentValue)}`;
    wrapper.appendChild(caption);
    wrapper.appendChild(renderFieldDescription(field));
    return wrapper;
}

/**
 * @param {unknown} rawInputValue
 * @param {FieldDef} field
 * @returns {unknown}
 */
function readInputValue(rawInputValue, field) {
    if (field.kind === "number") {
        return rawInputValue === "" ? undefined : Number(rawInputValue);
    }
    return rawInputValue;
}

/**
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
 * @type {Record<string, number>}
 */
const STATUS_SEVERITY = { Invalid: 0, Failed: 1, Unchanged: 2, Valid: 3 };

/**
 * @param {HTMLElement} card
 * @param {Record<string, string>} results
 * @param {string} descr
 */
function applyResultStyling(card, results, descr) {
    const values = Object.values(results);
    const worst = values.reduce(
        (acc, status) => (((STATUS_SEVERITY[status] ?? 3) < (STATUS_SEVERITY[acc] ?? 3)) ? status : acc),
        "Valid",
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
 * @param {FieldGroup} group
 * @param {Section} section
 * @param {Record<string, unknown>} currentValues
 * @param {() => void} onApplied called after a PUT resolves, to refresh current-value captions.
 * @returns {HTMLElement}
 */
function renderFieldGroup(group, section, currentValues, onApplied) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.groupKey = group.key;

    const heading = document.createElement("h3");
    heading.textContent = group.label;
    card.appendChild(heading);

    for (const field of group.fields) {
        card.appendChild(renderField(field, currentValues[field.key], Boolean(group.submit)));
    }

    if (group.submit) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "apply-button";
        button.textContent = group.submitLabel ?? "Apply";
        const resultEl = document.createElement("p");
        resultEl.className = "apply-result";
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
                resultEl.textContent = `Request failed: ${String(error)}`;
                card.dataset.applyStatus = "failed";
            } finally {
                button.disabled = false;
            }
        });
        card.appendChild(button);
        card.appendChild(resultEl);
    }

    return card;
}

/**
 * @param {import("./definitions.js").ErrcountGroup} group
 * @param {Record<string, {counter: number, history?: {TS: number, ErrType: string, ErrNum: number}[]}>} errcount
 * @returns {HTMLElement}
 */
function renderErrcountGroup(group, errcount) {
    const wrapper = document.createElement("div");

    const summary = document.createElement("div");
    summary.className = "errcount-summary";
    for (const moduleInfo of group.modules) {
        const entry = errcount[moduleInfo.key] ?? { counter: 0 };
        const tile = document.createElement("button");
        tile.type = "button";
        tile.className = "errcount-tile";
        tile.dataset.hasErrors = String(entry.counter > 0);
        tile.setAttribute("aria-expanded", "false");

        const count = document.createElement("div");
        count.className = "errcount-tile-count";
        count.textContent = String(entry.counter);
        const label = document.createElement("div");
        label.className = "errcount-tile-label";
        label.textContent = moduleInfo.label;
        tile.append(count, label);

        const list = document.createElement("ul");
        list.className = "history-list hidden";
        const history = entry.history ?? [];
        if (history.length === 0) {
            const empty = document.createElement("li");
            empty.className = "history-empty";
            empty.textContent = "No history recorded.";
            list.appendChild(empty);
        } else {
            // §8 resolution: no pagination/truncation - realistic history depth is well under
            // 20 entries (project owner, session 2), so the whole array just renders on expand.
            for (const item of history) {
                const li = document.createElement("li");
                li.className = "history-entry";
                const when = document.createElement("span");
                when.textContent = new Date(item.TS * 1000).toISOString().replace("T", " ").slice(0, 19);
                const what = document.createElement("span");
                what.textContent = `${item.ErrType} (errno ${item.ErrNum})`;
                li.append(when, what);
                list.appendChild(li);
            }
        }

        tile.addEventListener("click", () => {
            const expanded = tile.getAttribute("aria-expanded") === "true";
            tile.setAttribute("aria-expanded", String(!expanded));
            list.classList.toggle("hidden", expanded);
        });

        const tileWrapper = document.createElement("div");
        tileWrapper.appendChild(tile);
        tileWrapper.appendChild(list);
        summary.appendChild(tileWrapper);
    }
    wrapper.appendChild(summary);
    return wrapper;
}

/**
 * Renders `section` into `mainEl` and wires live polling if applicable.
 * @param {SiteDefinitions} defs
 * @param {Section} section
 * @param {HTMLElement} mainEl
 * @returns {() => void} stop function - call before switching to another section.
 */
export function renderSection(defs, section, mainEl) {
    mainEl.replaceChildren();

    const heading = document.createElement("h2");
    heading.className = "section-heading";
    heading.textContent = section.label;
    mainEl.appendChild(heading);
    if (section.description) {
        const desc = document.createElement("p");
        desc.className = "section-description";
        desc.textContent = section.description;
        mainEl.appendChild(desc);
    }

    const grid = document.createElement("div");
    grid.className = "group-grid";
    mainEl.appendChild(grid);

    /** @param {Record<string, unknown>} data */
    const paint = (data) => {
        for (const group of section.groups) {
            if ("kind" in group && group.kind === "errcount") {
                const errcountGroup = /** @type {import("./definitions.js").ErrcountGroup} */ (group);
                const errcount = /** @type {any} */ (data).errcount ?? {};
                const existing = grid.querySelector(`[data-group-key="${group.key}"]`);
                const rendered = renderErrcountGroup(errcountGroup, errcount);
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
                        caption.textContent = `Current value: ${formatValue(field, groupValues[field.key])}`;
                    }
                    const readonlySpan = existing.querySelector(`.field-value[data-field-key="${field.key}"]`);
                    if (readonlySpan) {
                        readonlySpan.textContent = formatValue(field, groupValues[field.key]);
                    }
                }
                continue;
            }
            const rendered = renderFieldGroup(fieldGroup, section, groupValues, () => void fetchOnce());
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
