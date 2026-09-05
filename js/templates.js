/**
 * Presentation layer - the visual half of the visual/mechanics split. Every DOM element this
 * app ever creates is built here, and only here; see SPECIFICATION.md Part H.3 for the full contract.
 */

// formatFieldValue() itself now lives in ./field-format.js (pure formatting, no DOM dependency -
// see that file's own header comment for why) - imported here for this file's own internal use,
// not re-exported: scripts/build_website.sh's own concatenation-based bundler leaves every file's
// `export` keywords as-is (never strips them, unlike `import` lines), so a second `export
// {formatFieldValue}` here would collide with field-format.js's own `export function
// formatFieldValue` once both are concatenated into one module - callers that need this function
// import it from js/field-format.js directly instead (js/render.js, tests_js/templates.test.js).
import { resolveFieldValue } from "./definitions.js";
import { formatFieldValue } from "./field-format.js";

/** @typedef {import("./definitions.js").FieldDef} FieldDef */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").ErrcountGroup} ErrcountGroup */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {FieldDef} field
 * @returns {HTMLElement}
 */
function buildFieldDescription(field) {
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
 * Builds one field's markup - label, control (or value span when not editable), description
 * hint. A toggle's own cosmetic On/Off flip is wired here (§12); every other control is left
 * inert for a controller to attach real behavior to, keyed off `data-field-key`.
 * @param {FieldDef} field
 * @param {unknown} currentValue
 * @param {boolean} editable
 * @returns {HTMLElement}
 */
export function buildField(field, currentValue, editable) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    // Distinct from data-field-key below (which must keep pointing at the specific control -
    // collectGroupBody()/paint() rely on that exact element) - this tags the whole per-field box
    // so a PUT result can color it individually (SPECIFICATION.md Part H.3, per-field granularity).
    wrapper.dataset.fieldWrapperKey = field.key;

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
        value.textContent = formatFieldValue(field, currentValue);
        wrapper.appendChild(value);
        wrapper.appendChild(buildFieldDescription(field));
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
        // Purely cosmetic self-flip - no network call, safe to wire directly here.
        button.addEventListener("click", () => {
            const next = button.dataset.value !== "true";
            button.dataset.value = String(next);
            button.setAttribute("aria-pressed", String(next));
            button.textContent = next ? (field.onLabel ?? "On") : (field.offLabel ?? "Off");
        });
        wrapper.appendChild(button);
        wrapper.appendChild(buildFieldDescription(field));
        return wrapper;
    }

    if (field.kind === "enum") {
        const select = document.createElement("select");
        select.id = `field-${field.key}`;
        select.dataset.fieldKey = field.key;
        const options = field.options ?? [];
        if (!options.some((option) => option.value === currentValue)) {
            // No real value to preselect (e.g. SystemCmd, a write-only dispatched action never
            // returned by GET /system) - without this, a native <select> with no <option> marked
            // selected defaults to its first one, so clicking Apply without ever touching the
            // dropdown would silently submit whichever command is listed first. Left unselected,
            // collectGroupBody()'s existing control.value === "" check omits it from the PUT body,
            // matching every other untouched field's own sparse-PUT convention.
            const placeholder = document.createElement("option");
            placeholder.value = "";
            placeholder.textContent = "Select…";
            placeholder.selected = true;
            select.appendChild(placeholder);
        }
        for (const option of options) {
            const optionEl = document.createElement("option");
            optionEl.value = String(option.value);
            optionEl.textContent = option.label;
            if (option.value === currentValue) {
                optionEl.selected = true;
            }
            select.appendChild(optionEl);
        }
        wrapper.appendChild(select);
        wrapper.appendChild(buildFieldDescription(field));
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
        wrapper.appendChild(buildFieldDescription(field));
        return wrapper;
    }

    // number or string
    const input = document.createElement("input");
    input.type = field.mask === true ? "password" : "text";
    input.id = `field-${field.key}`;
    input.dataset.fieldKey = field.key;
    input.value = "";
    input.placeholder = formatFieldValue(field, currentValue);
    wrapper.appendChild(input);

    const caption = document.createElement("p");
    caption.className = "field-description";
    caption.dataset.currentValueFor = field.key;
    caption.textContent = `Current value: ${formatFieldValue(field, currentValue)}`;
    wrapper.appendChild(caption);
    wrapper.appendChild(buildFieldDescription(field));
    return wrapper;
}

/**
 * Builds a field-group card: heading, every field, and - if the group is writable - an inert
 * `.apply-button`/`.apply-result` pair. The button has no click behavior yet; a controller
 * attaches the real submit logic by querying `.apply-button` on the returned card.
 * @param {FieldGroup} group
 * @param {Record<string, unknown>} currentValues
 * @returns {HTMLElement}
 */
export function buildFieldGroupCard(group, currentValues) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.groupKey = group.key;

    const heading = document.createElement("h3");
    heading.textContent = group.label;
    card.appendChild(heading);

    for (const field of group.fields) {
        card.appendChild(buildField(field, resolveFieldValue(field, currentValues), Boolean(group.submit)));
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
 * @param {{counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}} entry
 * @returns {"N"|"E"|"W"}
 */
function worstErrcountType(entry) {
    const history = entry.history ?? [];
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
 * @param {Record<string, {counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}>} errcount
 * @returns {HTMLElement}
 */
export function buildErrcountGroup(group, errcount) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.groupKey = group.key;

    const heading = document.createElement("h3");
    heading.textContent = group.label;
    card.appendChild(heading);

    const rows = group.modules.map((moduleInfo) => ({
        moduleInfo,
        entry: errcount[moduleInfo.key] ?? { counter: 0 },
        worst: worstErrcountType(errcount[moduleInfo.key] ?? { counter: 0 }),
    }));
    const errorCount = rows.filter((row) => row.worst === "E").length;
    const warningCount = rows.filter((row) => row.worst === "W").length;

    const rollup = document.createElement("div");
    rollup.className = "errcount-rollup";
    const errorsSpan = document.createElement("span");
    errorsSpan.className = "errcount-rollup-count";
    errorsSpan.dataset.rollup = "errors";
    errorsSpan.textContent = `${errorCount} module${errorCount === 1 ? "" : "s"} with errors`;
    const warningsSpan = document.createElement("span");
    warningsSpan.className = "errcount-rollup-count";
    warningsSpan.dataset.rollup = "warnings";
    warningsSpan.textContent = `${warningCount} module${warningCount === 1 ? "" : "s"} with warnings`;
    const flaggedButton = document.createElement("button");
    flaggedButton.type = "button";
    flaggedButton.className = "action-button";
    flaggedButton.textContent = "Show flagged";
    flaggedButton.dataset.errcountAction = "flagged";
    const allButton = document.createElement("button");
    allButton.type = "button";
    allButton.className = "action-button";
    allButton.textContent = "Show all";
    allButton.dataset.errcountAction = "all";
    rollup.append(errorsSpan, warningsSpan, flaggedButton, allButton);
    card.appendChild(rollup);

    const moduleList = document.createElement("div");
    moduleList.className = "errcount-module-list hidden";
    for (const { moduleInfo, entry, worst } of rows) {
        const rowWrapper = document.createElement("div");
        rowWrapper.className = "errcount-row-wrapper hidden";
        rowWrapper.dataset.worst = worst;

        const row = document.createElement("div");
        row.className = "errcount-row";
        row.dataset.hasErrors = String(entry.counter > 0);
        const name = document.createElement("span");
        name.className = "errcount-row-name";
        name.textContent = moduleInfo.label;
        const count = document.createElement("span");
        count.className = "errcount-row-count";
        count.textContent = String(entry.counter);
        row.append(name, count);

        // Always rendered, never independently hidden - a shown row's history is meant to be
        // visible right away, not gated behind a second click (project owner, session 2 follow-up).
        const list = document.createElement("ul");
        list.className = "history-list";
        const history = entry.history ?? [];
        if (history.length === 0) {
            const empty = document.createElement("li");
            empty.className = "history-empty";
            empty.textContent = "No history recorded.";
            list.appendChild(empty);
        } else {
            // §8 resolution: no pagination/truncation - realistic history depth is well under
            // 20 entries (project owner, session 2), so the whole array just renders.
            for (const item of history) {
                const li = document.createElement("li");
                li.className = "history-entry";
                li.dataset.errType = item.type;
                const num = document.createElement("span");
                num.className = "history-entry-num";
                num.textContent = String(item.num);
                li.appendChild(num);
                list.appendChild(li);
            }
        }

        rowWrapper.append(row, list);
        moduleList.appendChild(rowWrapper);
    }
    card.appendChild(moduleList);

    flaggedButton.addEventListener("click", () => {
        moduleList.classList.remove("hidden");
        for (const rowWrapper of /** @type {HTMLElement[]} */ ([...moduleList.children])) {
            rowWrapper.classList.toggle("hidden", rowWrapper.dataset.worst === "N");
        }
    });
    allButton.addEventListener("click", () => {
        moduleList.classList.remove("hidden");
        for (const rowWrapper of /** @type {HTMLElement[]} */ ([...moduleList.children])) {
            rowWrapper.classList.remove("hidden");
        }
    });

    return card;
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
    errorBanner.className = "error-banner hidden";
    errorBanner.setAttribute("role", "alert");
    mainEl.appendChild(errorBanner);

    const grid = document.createElement("div");
    grid.className = "group-grid";
    mainEl.appendChild(grid);
    return { grid, errorBanner };
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
