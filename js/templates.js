/**
 * Presentation layer - the visual half of the visual/mechanics split. Every DOM element this
 * app ever creates is built here, and only here; see SPECIFICATION.md Part H.3 for the full contract.
 */

// formatFieldValue() is imported for internal use only, never re-exported: the stager rejects `export … from` and a name
// exported twice (SPECIFICATION.md Part H.2's splitting rule). Callers import it from ./field-format.js.
import { ERR_COUNT_CAP, isUnavailable } from "./api-contract.js";
import { resolveFieldValue } from "./definitions.js";
import { formatFieldValue } from "./field-format.js";

/** @typedef {import("./definitions.js").FieldDef} FieldDef */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").ErrcountGroup} ErrcountGroup */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */
/**
 * What a card shows beside its values: the device's clock for ages, the definitions' default decimals, and
 * which fields the device could not read.
 * @typedef {{deviceNowS: number | null, defaultDecimals?: number | undefined, isUnavailable: (field: FieldDef) => boolean}} CardDisplay
 */
/** @typedef {{deviceNowS: number | null, defaultDecimals: number | undefined, unavailable: boolean, siblingLabel: string | undefined}} FieldDisplay */
/** @typedef {{num: number, type: "N"|"E"|"W"}} HistoryItem */
/** @typedef {{count: string, worst: "N"|"E"|"W"|"none", history: HistoryItem[] | null}} ErrcountRowState */

const SOURCE_UNAVAILABLE_TEXT = "unavailable";
const NO_DATA_TEXT = "no data";
const UNSET_TOGGLE_TEXT = "—";
// The form each string shape takes: src/asy_dns_client.py's host_label_ok(), src/asy_ntp_client.py's _ntp_host_ok()
// and _dns_fallback_ok() (its _DNS_FALLBACK_MAX servers); a country code's own description states its form.
/** @type {Partial<Record<NonNullable<FieldDef["shape"]>, string>>} */
const STRING_SHAPE_HINTS = {
    hostLabel: "letters, digits and '-' only",
    hostName: "a host name (letters, digits, '-' and '.') or an IPv4 address",
    ipv4List: "up to 3 IPv4 addresses, comma-separated, no spaces",
};

/**
 * Shows the rows the list's filter (`collapsed`, `flagged` or `all`) selects; flagged is every row not `N`.
 * @param {HTMLElement} moduleList
 */
function applyErrcountFilter(moduleList) {
    const { filter } = moduleList.dataset;
    moduleList.classList.toggle("hidden", filter === "collapsed");
    for (const rowWrapper of /** @type {HTMLElement[]} */ ([...moduleList.children])) {
        rowWrapper.classList.toggle("hidden", filter === "collapsed" || (filter === "flagged" && rowWrapper.dataset.worst === "N"));
    }
}

/**
 * @param {FieldDef} field
 * @param {string} fieldId
 * @returns {HTMLElement}
 */
function buildCompositeControl(field, fieldId) {
    const grid = document.createElement("div");
    grid.className = "composite-fields";
    grid.dataset.fieldKey = field.key;
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-labelledby", `${fieldId}-label`);
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
    return grid;
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {string} fieldId
 * @returns {HTMLElement}
 */
function buildEnumControl(field, value, fieldId) {
    const select = document.createElement("select");
    select.id = fieldId;
    select.dataset.fieldKey = field.key;
    const options = field.options ?? [];
    if (!options.some((option) => option.value === value)) {
        // No value to preselect (SystemCmd is write-only, never returned by GET /system).
        // A native <select> with nothing selected defaults to its first option, so Apply
        // would submit whichever command is listed first without anyone choosing it.

        // Left unselected, collectGroupBody()'s control.value === "" check omits it from the
        // body, which is the same sparse-PUT convention every untouched field follows.
        select.appendChild(buildSelectPlaceholder());
    }
    for (const option of options) {
        const optionEl = document.createElement("option");
        optionEl.value = String(option.value);
        optionEl.textContent = option.label;
        if (option.value === value) {
            optionEl.selected = true;
        }
        select.appendChild(optionEl);
    }
    return select;
}

/**
 * @param {HTMLElement} moduleList
 * @param {string} label
 * @param {"flagged" | "all"} filter
 * @returns {HTMLElement}
 */
function buildErrcountFilterButton(moduleList, label, filter) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "action-button";
    button.textContent = label;
    button.dataset.errcountAction = filter;
    button.addEventListener("click", () => {
        moduleList.dataset.filter = filter;
        applyErrcountFilter(moduleList);
    });
    return button;
}

/**
 * Builds one field's markup - label, control (or value element when not editable), description hint.
 * A toggle's cosmetic flip and a code's description are wired here (SPECIFICATION.md Part H.3); every
 * other control is left inert for a controller to wire, keyed off `data-field-key`.
 * @param {FieldDef} field
 * @param {unknown} currentValue
 * @param {boolean} editable
 * @param {string} fieldId `field-<groupIndex>-<fieldIndex>`
 * @param {FieldDisplay} display
 * @returns {HTMLElement}
 */
function buildField(field, currentValue, editable, fieldId, display) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    // Distinct from data-field-key below (which must keep pointing at the specific control -
    // collectGroupBody()/paint() rely on that exact element) - this tags the whole per-field box
    // so a PUT result can color it individually (SPECIFICATION.md Part H.3, per-field granularity).
    wrapper.dataset.fieldWrapperKey = field.key;

    const readonly = !editable || field.kind === "readonly";
    wrapper.appendChild(buildFieldLabel(field, fieldId, !readonly && field.kind !== "composite"));
    if (readonly) {
        wrapper.appendChild(buildReadonlyValue(field, currentValue, fieldId, display));
    } else if (field.kind === "toggle") {
        wrapper.appendChild(buildToggleControl(field, currentValue, fieldId));
    } else if (field.kind === "enum") {
        wrapper.appendChild(buildEnumControl(field, currentValue, fieldId));
    } else if (field.kind === "composite") {
        wrapper.appendChild(buildCompositeControl(field, fieldId));
    } else {
        wrapper.append(...buildTextControls(field, currentValue, fieldId, display));
    }
    wrapper.appendChild(buildFieldDescription(field));
    return wrapper;
}

/**
 * @param {FieldDef} field
 * @returns {HTMLElement}
 */
function buildFieldDescription(field) {
    const parts = fieldBoundHints(field);
    const shapeHint = field.shape === undefined ? undefined : STRING_SHAPE_HINTS[field.shape];
    if (shapeHint !== undefined) {
        parts.push(shapeHint);
    }
    // Specials in the hint for a number or string field only: a readonly field's specials name values it shows.
    for (const special of field.kind === "number" || field.kind === "string" ? (field.specialValues ?? []) : []) {
        parts.push(`${typeof special.value === "string" ? JSON.stringify(special.value) : special.value} = ${special.meaning}`);
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
 * A control with an id gets a `label` bound to it; a readonly value or a composite gets a span with
 * its own id, which the value or grid names through aria-labelledby.
 * @param {FieldDef} field
 * @param {string} fieldId
 * @param {boolean} forControl
 * @returns {HTMLElement}
 */
function buildFieldLabel(field, fieldId, forControl) {
    const label = document.createElement(forControl ? "label" : "span");
    label.className = "field-label";
    if (label instanceof HTMLLabelElement) {
        label.htmlFor = fieldId;
    } else {
        label.id = `${fieldId}-label`;
    }
    label.textContent = field.label;
    if (field.unit) {
        const unitSpan = document.createElement("span");
        unitSpan.className = "field-unit";
        unitSpan.textContent = ` [${field.unit}]`;
        label.appendChild(unitSpan);
    }
    return label;
}

/**
 * An error or warning number is a button showing its code's description; a no-error one stays text.
 * @param {HTMLElement} list
 * @param {ErrcountGroup} group
 * @param {HistoryItem} item
 * @returns {HTMLElement}
 */
function buildHistoryEntry(list, group, item) {
    const li = document.createElement("li");
    li.className = "history-entry";
    li.dataset.errType = item.type;
    const num = document.createElement(item.type === "N" ? "span" : "button");
    num.className = "history-entry-num";
    num.textContent = String(item.num);
    if (num instanceof HTMLButtonElement) {
        num.type = "button";
        num.setAttribute("aria-expanded", "false");
        const codes = item.type === "N" ? undefined : group.codes?.[item.type];
        num.addEventListener("click", () => {
            toggleHistoryDescription(list, num, describeCode(codes, String(item.num)));
        });
    }
    li.appendChild(num);
    return li;
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {string} fieldId
 * @param {FieldDisplay} display
 * @returns {HTMLElement}
 */
function buildReadonlyValue(field, value, fieldId, display) {
    /** @type {HTMLElement} */
    let el;
    if (field.codes !== undefined && field.codeTones === undefined) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "field-value code-value";
        button.id = fieldId;
        button.setAttribute("aria-expanded", "false");
        button.setAttribute("aria-labelledby", `${fieldId}-label ${fieldId}`);
        button.addEventListener("click", () => {
            if (button.getAttribute("aria-expanded") === "true") {
                closeCodeDescription(button);
                button.setAttribute("aria-expanded", "false");
            } else {
                openCodeDescription(button, button, describeCode(field.codes, button.value));
            }
        });
        el = button;
    } else {
        el = document.createElement("span");
        el.className = "field-value";
        el.setAttribute("aria-labelledby", `${fieldId}-label`);
    }
    el.dataset.fieldKey = field.key;
    paintReadonlyValue(el, field, value, display);
    return el;
}

/**
 * @param {string} rollup
 * @returns {HTMLElement}
 */
function buildRollupCount(rollup) {
    const span = document.createElement("span");
    span.className = "errcount-rollup-count";
    span.dataset.rollup = rollup;
    return span;
}

/**
 * @returns {HTMLOptionElement}
 */
function buildSelectPlaceholder() {
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select…";
    placeholder.selected = true;
    return placeholder;
}

/**
 * A number/string input starts empty with the current value as placeholder and caption, then the
 * Clear button of a clearable string and the warning of a field another one overrides.
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {string} fieldId
 * @param {FieldDisplay} display
 * @returns {HTMLElement[]}
 */
function buildTextControls(field, value, fieldId, display) {
    const text = currentValueText(field, value, display);
    const input = document.createElement("input");
    input.type = field.mask === true ? "password" : "text";
    if (field.mask === true) {
        input.setAttribute("autocomplete", "new-password");
    }
    input.id = fieldId;
    input.dataset.fieldKey = field.key;
    input.value = "";
    input.placeholder = text;
    /** @type {HTMLElement[]} */
    const controls = [input];

    if (field.clearable === true && field.kind === "string") {
        const clear = document.createElement("button");
        clear.type = "button";
        clear.className = "action-button clear-button";
        clear.dataset.clearFor = fieldId;
        clear.textContent = "Clear";
        controls.push(clear);
    }

    const caption = document.createElement("p");
    caption.className = "field-description";
    caption.dataset.currentValueFor = field.key;
    caption.textContent = `Current value: ${text}`;
    controls.push(caption);

    if (field.ignoredWhenSet !== undefined) {
        const warning = document.createElement("p");
        warning.className = "field-warning";
        warning.dataset.shown = "false";
        warning.textContent = `Ignored: ${display.siblingLabel ?? field.ignoredWhenSet} is set.`;
        controls.push(warning);
    }
    return controls;
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {string} fieldId
 * @returns {HTMLElement}
 */
function buildToggleControl(field, value, fieldId) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "toggle-button";
    button.id = fieldId;
    button.dataset.fieldKey = field.key;
    paintToggle(button, field, toggleStateOf(field, value));
    // Purely cosmetic self-flip - no network call, safe to wire directly here.
    button.addEventListener("click", () => {
        paintToggle(button, field, button.dataset.value !== "true");
    });
    return button;
}

/**
 * @param {HTMLElement} anchor
 */
function closeCodeDescription(anchor) {
    const description = anchor.nextElementSibling;
    if (description instanceof HTMLParagraphElement && description.classList.contains("code-description")) {
        description.remove();
    }
}

/**
 * @param {unknown} value
 * @returns {string | undefined} the code a code field shows, undefined when the value is none
 */
function codeOf(value) {
    return typeof value === "number" || typeof value === "string" ? String(value) : undefined;
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {FieldDisplay} display
 * @returns {string} what a number/string field shows as its current value
 */
function currentValueText(field, value, display) {
    return display.unavailable ? SOURCE_UNAVAILABLE_TEXT : formatFieldValue(field, value, display);
}

/**
 * @param {Record<string, string> | undefined} codes
 * @param {string} code
 * @returns {string}
 */
function describeCode(codes, code) {
    return codes !== undefined && Object.hasOwn(codes, code) ? `${code}: ${codes[code]}` : `No description for code ${code}`;
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @returns {string | null} the ISO-8601 UTC instant of an epoch value, null for any other value
 */
function epochInstant(field, value) {
    if (field.format !== "epoch" || typeof value !== "number" || (field.specialValues ?? []).some((special) => special.value === value)) {
        return null;
    }
    const instant = new Date(value * 1000);
    return Number.isNaN(instant.getTime()) ? null : instant.toISOString();
}

/**
 * @param {unknown} entry one module's errcount entry; undefined when the body carried none
 * @returns {ErrcountRowState} the row's count text, its one severity and its history (null when there is no data)
 */
function errcountRowState(entry) {
    if (isUnavailable(entry)) {
        return { count: SOURCE_UNAVAILABLE_TEXT, worst: "none", history: null };
    }
    if (typeof entry !== "object" || entry === null) {
        return { count: NO_DATA_TEXT, worst: "none", history: null };
    }
    const { counter, history } = /** @type {{counter: unknown, history?: unknown}} */ (entry);
    const items = Array.isArray(history) ? /** @type {HistoryItem[]} */ (history) : [];
    const count = typeof counter === "number" && counter >= ERR_COUNT_CAP ? `${ERR_COUNT_CAP}+` : String(counter);
    return { count, worst: worstErrcountType(items), history: items };
}

/**
 * @param {FieldDef} field
 * @returns {string[]} a number's range, a string's length and a value's resolution, each as its hint text
 */
function fieldBoundHints(field) {
    const unit = field.unit ? ` ${field.unit}` : "";
    const hints = [];
    if (field.kind === "number" && (field.min !== undefined || field.max !== undefined)) {
        hints.push(`Valid values: ${field.min ?? "–∞"} to ${field.max ?? "∞"}${unit}`);
    }
    if (field.kind === "string" && (field.minLength !== undefined || field.maxLength !== undefined)) {
        const bytes = field.byteLength && field.maxLength !== undefined ? `, at most ${field.maxLength} bytes (UTF-8)` : "";
        hints.push(`Length: ${field.minLength ?? 0} to ${field.maxLength ?? "∞"} characters${bytes}`);
    }
    if (field.resolution !== undefined) {
        hints.push(`Resolution: ${field.resolution}${unit}`);
    }
    return hints;
}

/**
 * @param {FieldGroup} group
 * @param {FieldDef} field
 * @param {CardDisplay} display
 * @returns {FieldDisplay}
 */
function fieldDisplayOf(group, field, display) {
    const sibling = field.ignoredWhenSet === undefined ? undefined : group.fields.find((candidate) => candidate.key === field.ignoredWhenSet);
    return { deviceNowS: display.deviceNowS, defaultDecimals: display.defaultDecimals, unavailable: display.isUnavailable(field), siblingLabel: sibling?.label };
}

/**
 * @param {HistoryItem[] | null} history
 * @returns {string} the history as the list shows it, so an update rebuilds only a changed one
 */
function historySignature(history) {
    if (history === null) {
        return "";
    }
    return history.length === 0 ? "empty" : history.map((item) => `${item.type}${item.num}`).join(",");
}

/**
 * @param {number} count
 * @param {string} what
 * @returns {string}
 */
function modulesText(count, what) {
    return `${count} module${count === 1 ? "" : "s"} ${what}`;
}

/**
 * Shows `text` in the code description right after `anchor`, opened by `button`.
 * @param {HTMLElement} anchor
 * @param {HTMLElement} button
 * @param {string} text
 */
function openCodeDescription(anchor, button, text) {
    let description = anchor.nextElementSibling;
    if (!(description instanceof HTMLParagraphElement && description.classList.contains("code-description"))) {
        description = document.createElement("p");
        description.className = "code-description";
        anchor.after(description);
    }
    description.textContent = text;
    button.setAttribute("aria-expanded", "true");
}

/**
 * A code shows its number on a button whose click shows the code's description; with no code to
 * describe the button is disabled and an open description closes.
 * @param {HTMLButtonElement} button
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {FieldDisplay} display
 */
function paintCodeButton(button, field, value, display) {
    const code = display.unavailable ? undefined : codeOf(value);
    button.value = code ?? "";
    button.disabled = code === undefined;
    if (code === undefined) {
        button.textContent = display.unavailable ? SOURCE_UNAVAILABLE_TEXT : formatFieldValue(field, value, display);
    } else {
        button.textContent = code;
    }
    if (button.getAttribute("aria-expanded") !== "true") {
        return;
    }
    if (code === undefined) {
        closeCodeDescription(button);
        button.setAttribute("aria-expanded", "false");
    } else {
        openCodeDescription(button, button, describeCode(field.codes, code));
    }
}

/**
 * Paints every row, the rollup and the current filter from `errcount`; never replaces a button or the list.
 * @param {HTMLElement} card
 * @param {ErrcountGroup} group
 * @param {Record<string, unknown> | null} errcount
 */
function paintErrcountGroup(card, group, errcount) {
    const moduleList = card.querySelector(".errcount-module-list");
    if (!(moduleList instanceof HTMLElement)) {
        return;
    }
    const rowWrappers = /** @type {HTMLElement[]} */ ([...moduleList.children]);
    const tally = { E: 0, W: 0, N: 0, none: 0 };
    for (const [index, moduleInfo] of group.modules.entries()) {
        const entry = errcount !== null && Object.hasOwn(errcount, moduleInfo.key) ? errcount[moduleInfo.key] : undefined;
        const state = errcountRowState(entry);
        tally[state.worst] += 1;
        const rowWrapper = rowWrappers[index];
        if (rowWrapper !== undefined) {
            paintErrcountRow(rowWrapper, group, state);
        }
    }
    paintRollupText(card, "errors", modulesText(tally.E, "with errors"));
    paintRollupText(card, "warnings", modulesText(tally.W, "with warnings"));
    paintRollupText(card, "nodata", modulesText(tally.none, "without data"));
    card.querySelector('[data-rollup="nodata"]')?.classList.toggle("hidden", tally.none === 0);
    applyErrcountFilter(moduleList);
}

/**
 * @param {HTMLElement} rowWrapper
 * @param {ErrcountGroup} group
 * @param {ErrcountRowState} state
 */
function paintErrcountRow(rowWrapper, group, state) {
    rowWrapper.dataset.worst = state.worst;
    const count = rowWrapper.querySelector(".errcount-row-count");
    const list = rowWrapper.querySelector(".history-list");
    if (count === null || !(list instanceof HTMLElement)) {
        return;
    }
    count.textContent = state.count;
    if (shownHistorySignature(list) === historySignature(state.history)) {
        return;
    }
    closeCodeDescription(list);
    if (state.history === null) {
        list.replaceChildren();
    } else if (state.history.length === 0) {
        const empty = document.createElement("li");
        empty.className = "history-empty";
        empty.textContent = "No history recorded.";
        list.replaceChildren(empty);
    } else {
        // No pagination or truncation - realistic history depth is well under
        // 20 entries (owner, 2026-08-21), so the whole array just renders.
        list.replaceChildren(...state.history.map((item) => buildHistoryEntry(list, group, item)));
    }
}

/**
 * Gives a readonly value element its text, and its title, code button or tone, from `value`.
 * @param {HTMLElement} el
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {FieldDisplay} display
 */
function paintReadonlyValue(el, field, value, display) {
    if (field.codeTones !== undefined) {
        paintTonedCode(el, field, value, display);
        return;
    }
    if (el instanceof HTMLButtonElement) {
        paintCodeButton(el, field, value, display);
        return;
    }
    el.textContent = display.unavailable ? SOURCE_UNAVAILABLE_TEXT : formatFieldValue(field, value, display);
    const instant = display.unavailable ? null : epochInstant(field, value);
    if (instant === null) {
        el.removeAttribute("title");
    } else {
        el.title = instant;
    }
}

/**
 * @param {HTMLElement} card
 * @param {string} rollup
 * @param {string} text
 */
function paintRollupText(card, rollup, text) {
    const span = card.querySelector(`[data-rollup="${CSS.escape(rollup)}"]`);
    if (span !== null) {
        span.textContent = text;
    }
}

/**
 * @param {HTMLElement} button
 * @param {FieldDef} field
 * @param {boolean | undefined} state
 */
function paintToggle(button, field, state) {
    if (state === undefined) {
        button.dataset.value = "unset";
        button.setAttribute("aria-pressed", "mixed");
        button.textContent = UNSET_TOGGLE_TEXT;
        return;
    }
    button.dataset.value = String(state);
    button.setAttribute("aria-pressed", String(state));
    button.textContent = state ? (field.onLabel ?? "On") : (field.offLabel ?? "Off");
}

/**
 * A code with a tone shows its text, then its number muted; an unknown code its number alone.
 * @param {HTMLElement} span
 * @param {FieldDef} field
 * @param {unknown} value
 * @param {FieldDisplay} display
 */
function paintTonedCode(span, field, value, display) {
    const code = display.unavailable ? undefined : codeOf(value);
    if (code === undefined) {
        span.textContent = display.unavailable ? SOURCE_UNAVAILABLE_TEXT : formatFieldValue(field, value, display);
        delete span.dataset.codeTone;
        return;
    }
    const number = document.createElement("span");
    number.className = "code-number";
    number.textContent = `(${code})`;
    const known = field.codes !== undefined && Object.hasOwn(field.codes, code);
    span.replaceChildren(...(known ? [`${field.codes?.[code]} `, number] : [number]));
    const tone = known && field.codeTones !== undefined && Object.hasOwn(field.codeTones, code) ? field.codeTones[code] : undefined;
    if (tone === undefined) {
        delete span.dataset.codeTone;
    } else {
        span.dataset.codeTone = tone;
    }
}

/**
 * @param {HTMLElement} list
 * @returns {string} what historySignature() gave the history the list shows now
 */
function shownHistorySignature(list) {
    const items = [...list.children].map((li) => (li instanceof HTMLElement && li.classList.contains("history-entry") ? `${li.dataset.errType}${li.textContent}` : "empty"));
    return items.length === 1 && items[0] === "empty" ? "empty" : items.join(",");
}

/**
 * @param {HTMLElement} list the row's history list, after which its one code description sits
 * @param {HTMLElement} pill
 * @param {string} text
 */
function toggleHistoryDescription(list, pill, text) {
    const wasOpen = pill.getAttribute("aria-expanded") === "true";
    for (const other of list.querySelectorAll("button.history-entry-num")) {
        other.setAttribute("aria-expanded", "false");
    }
    if (wasOpen) {
        closeCodeDescription(list);
    } else {
        openCodeDescription(list, pill, text);
    }
}

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @returns {boolean | undefined} a toggle's shown state; undefined (unset) for an always-executed toggle with no value
 */
function toggleStateOf(field, value) {
    return field.alwaysExecuted === true && value === undefined ? undefined : Boolean(value);
}

/**
 * @param {HistoryItem[]} history
 * @returns {"N"|"E"|"W"}
 */
function worstErrcountType(history) {
    if (history.some((item) => item.type === "E")) {
        return "E";
    }
    if (history.some((item) => item.type === "W")) {
        return "W";
    }
    return "N";
}

/**
 * Builds the Status page's error-count card: collapsed rollup + filter buttons, entries colored
 * (never captioned) by their raw errno's type. See SPECIFICATION.md Part H.6's "Errcount UX"
 * and "History entry shape" for the full rationale.
 * @param {ErrcountGroup} group
 * @param {Record<string, unknown> | null} errcount the `/status` body's errcount object; null when it carried none
 * @returns {HTMLElement}
 */
export function buildErrcountGroup(group, errcount) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.groupKey = group.key;

    const heading = document.createElement("h3");
    heading.textContent = group.label;
    card.appendChild(heading);

    const moduleList = document.createElement("div");
    moduleList.className = "errcount-module-list hidden";
    moduleList.dataset.filter = "collapsed";

    const rollup = document.createElement("div");
    rollup.className = "errcount-rollup";
    rollup.append(
        buildRollupCount("errors"),
        buildRollupCount("warnings"),
        buildRollupCount("nodata"),
        buildErrcountFilterButton(moduleList, "Show flagged", "flagged"),
        buildErrcountFilterButton(moduleList, "Show all", "all"),
    );
    card.appendChild(rollup);

    for (const moduleInfo of group.modules) {
        const rowWrapper = document.createElement("div");
        rowWrapper.className = "errcount-row-wrapper hidden";
        const row = document.createElement("div");
        row.className = "errcount-row";
        const name = document.createElement("span");
        name.className = "errcount-row-name";
        name.textContent = moduleInfo.label;
        const count = document.createElement("span");
        count.className = "errcount-row-count";
        row.append(name, count);

        // Always rendered, never independently hidden - a shown row's history is meant to be
        // visible right away, not gated behind a second click (owner, 2026-08-21).
        const list = document.createElement("ul");
        list.className = "history-list";
        rowWrapper.append(row, list);
        moduleList.appendChild(rowWrapper);
    }
    card.appendChild(moduleList);

    paintErrcountGroup(card, group, errcount);
    return card;
}

/**
 * Builds a field-group card: heading, every field, and - if the group is writable - an inert
 * `.apply-button`/`.apply-result` pair. The button has no click behavior yet; a controller
 * attaches the real submit logic by querying `.apply-button` on the returned card.
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} currentValues
 * @param {number} groupIndex the group's index in its section: field ids are `field-<groupIndex>-<fieldIndex>`
 * @param {CardDisplay} display
 * @returns {HTMLElement}
 */
export function buildFieldGroupCard(group, currentValues, groupIndex, display) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.groupKey = group.key;

    const heading = document.createElement("h3");
    heading.textContent = group.label;
    card.appendChild(heading);

    for (const [fieldIndex, field] of group.fields.entries()) {
        const fieldId = `field-${groupIndex}-${fieldIndex}`;
        card.appendChild(buildField(field, resolveFieldValue(field, currentValues), Boolean(group.submit), fieldId, fieldDisplayOf(group, field, display)));
    }

    if (group.submit) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "apply-button";
        button.textContent = group.submitLabel ?? "Apply";
        const resultEl = document.createElement("p");
        resultEl.className = "apply-result";
        card.appendChild(button);
        card.appendChild(resultEl);
    }

    return card;
}

/**
 * Builds the nav drawer's contents into `drawerEl`: a device-name heading, then one
 * `[data-section-key]` link per section. Links are inert - a controller (`nav.js`) attaches the
 * real section-switching behavior by querying `[data-section-key]`.
 * @param {SiteDefinitions} defs
 * @param {HTMLElement} drawerEl
 */
export function buildNavDrawer(defs, drawerEl) {
    drawerEl.replaceChildren();

    const heading = document.createElement("div");
    heading.className = "nav-drawer-heading";
    heading.textContent = defs.device.displayName;
    drawerEl.appendChild(heading);

    for (const section of defs.sections) {
        const link = document.createElement("button");
        link.type = "button";
        link.className = "nav-link";
        link.dataset.sectionKey = section.key;
        link.textContent = section.label;
        drawerEl.appendChild(link);
    }
}

/**
 * Builds a section's static shell (heading + description) into `mainEl`, plus an empty group
 * grid and an inert error banner for a controller to use. See SPECIFICATION.md Part H.3's "One
 * deliberate exception" note for why this returns `{grid, errorBanner}` directly.
 * @param {Section} section
 * @param {HTMLElement} mainEl
 * @returns {{grid: HTMLElement, errorBanner: HTMLElement}}
 */
export function buildSectionShell(section, mainEl) {
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

    const errorBanner = document.createElement("p");
    errorBanner.className = "error-banner";
    errorBanner.dataset.shown = "false";
    errorBanner.setAttribute("role", "alert");
    mainEl.appendChild(errorBanner);

    const grid = document.createElement("div");
    grid.className = "group-grid";
    mainEl.appendChild(grid);
    return { grid, errorBanner };
}

/**
 * Shows `value` in a field's control: clears a text input and every composite sub-input, sets a toggle
 * (unset for an always-executed toggle given undefined) with its label and aria-pressed, selects the
 * matching option or the placeholder.
 * @param {HTMLElement} wrapper the field's `[data-field-wrapper-key]` element
 * @param {FieldDef} field
 * @param {unknown} value
 */
export function resetControl(wrapper, field, value) {
    const control = wrapper.querySelector(`[data-field-key="${CSS.escape(field.key)}"]`);
    if (control instanceof HTMLSelectElement) {
        const match = (field.options ?? []).find((option) => option.value === value);
        if (match !== undefined) {
            control.value = String(match.value);
            return;
        }
        const placeholder = [...control.options].find((option) => option.value === "");
        if (placeholder === undefined) {
            control.prepend(buildSelectPlaceholder());
        } else {
            placeholder.selected = true;
        }
    } else if (control instanceof HTMLButtonElement && field.kind === "toggle") {
        paintToggle(control, field, toggleStateOf(field, value));
    } else if (control instanceof HTMLInputElement) {
        control.value = "";
    } else {
        for (const input of wrapper.querySelectorAll("input")) {
            input.value = "";
        }
    }
}

/**
 * Updates a built errcount card in place: rollup, each row's count, severity and changed history, and the
 * chosen filter; the buttons and the list stay the same elements, so focus stays.
 * @param {HTMLElement} card
 * @param {ErrcountGroup} group
 * @param {Record<string, unknown> | null} errcount the `/status` body's errcount object; null when it carried none
 */
export function updateErrcountGroup(card, group, errcount) {
    paintErrcountGroup(card, group, errcount);
}

/**
 * Refreshes a built card in place from new values: every readonly value, and every number/string caption
 * and placeholder; a toggle or select changes only by the user or by resetControl().
 * @param {HTMLElement} card
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} currentValues
 * @param {CardDisplay} display
 */
export function updateFieldGroupValues(card, group, currentValues, display) {
    for (const field of group.fields) {
        const value = resolveFieldValue(field, currentValues);
        const fieldDisplay = fieldDisplayOf(group, field, display);
        const control = card.querySelector(`[data-field-key="${CSS.escape(field.key)}"]`);
        if (!group.submit || field.kind === "readonly") {
            if (control instanceof HTMLElement) {
                paintReadonlyValue(control, field, value, fieldDisplay);
            }
        } else if (control instanceof HTMLInputElement) {
            const text = currentValueText(field, value, fieldDisplay);
            control.placeholder = text;
            const caption = card.querySelector(`[data-current-value-for="${CSS.escape(field.key)}"]`);
            if (caption !== null) {
                caption.textContent = `Current value: ${text}`;
            }
        }
    }
}
