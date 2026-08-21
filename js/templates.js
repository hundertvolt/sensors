/**
 * Presentation layer (WEBSITE_PLAN.md §12): every DOM element this app ever creates - its
 * structure, order, nesting, and CSS classes - is built here, and only here. This is the file (plus
 * `html/style.css`) a purely visual/layout redesign touches; it never fetches data, validates
 * input, or calls the REST API. The only interactivity here is self-contained and non-networked
 * (a toggle flipping its own On/Off label, an errcount tile expanding its own history list) -
 * anything that talks to the network or the poll-manager lives in a controller (`render.js`/
 * `nav.js`) instead, which locates the elements built here purely via the `data-*`
 * attributes/CSS classes documented in WEBSITE_PLAN.md §12's contract table, never by structural
 * position. Redesigning "what this looks like" or "what order things appear in" only ever means
 * editing this file and `html/style.css` - never `js/poll-manager.js`, `js/mock-server.js`,
 * `js/definitions.js`, or the business-logic half of `js/render.js`/`js/nav.js`.
 */

/** @typedef {import("./definitions.js").FieldDef} FieldDef */
/** @typedef {import("./definitions.js").FieldGroup} FieldGroup */
/** @typedef {import("./definitions.js").ErrcountGroup} ErrcountGroup */
/** @typedef {import("./definitions.js").Section} Section */
/** @typedef {import("./definitions.js").SiteDefinitions} SiteDefinitions */

/**
 * @param {FieldDef} field
 * @param {unknown} value
 * @returns {string}
 */
export function formatFieldValue(field, value) {
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
    if (field.format === "gmtimestruct") {
        // Real shape: src/sensortask_wozi.py's _gmtimestruct_to_dict() - {year, month, mday, hour,
        // minute, second, weekday} (weekday unused here), never a pre-formatted string.
        const t = /** @type {{year: number, month: number, mday: number, hour: number, minute: number, second: number}} */ (value);
        const pad = (/** @type {number} */ n) => String(n).padStart(2, "0");
        return `${t.year}-${pad(t.month)}-${pad(t.mday)} ${pad(t.hour)}:${pad(t.minute)}:${pad(t.second)}`;
    }
    return String(value);
}

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
 * Builds one field's markup - label, its control (or a plain value span when not editable), and
 * its description/range hint. A toggle's own On/Off flip is wired here since it's purely
 * cosmetic (no network call, no validation); every other control is left inert - a controller
 * attaches the real (networked) behavior separately, keyed off this element's `data-field-key`.
 * @param {FieldDef} field
 * @param {unknown} currentValue
 * @param {boolean} editable
 * @returns {HTMLElement}
 */
export function buildField(field, currentValue, editable) {
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
        for (const option of field.options ?? []) {
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
        card.appendChild(buildField(field, currentValues[field.key], Boolean(group.submit)));
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
 * Builds the Status page's error-count card: same `.card` shell every other field group uses
 * (heading + bordered/shadowed body - project owner, session 2 follow-up: the rollup/buttons were
 * floating loose on the page, unlike every other displayed value), starting fully collapsed to
 * just a rollup ("N modules with errors" / "M modules with warnings") plus two filter buttons
 * ("Show flagged"/"Show all") - a device can have 15+ registered modules, and showing every one of
 * them by default was too much vertical space for a page a visitor mostly just needs to glance at.
 * Choosing a filter is purely cosmetic (never touches the network), so it's wired here. Once a
 * module row is revealed by either filter, its history is shown immediately alongside it - no
 * further per-row click needed (project owner: a collapsed history on an already-revealed,
 * already-flagged module read as broken, not as a second layer of hiding).
 *
 * Each history entry is the raw errno (`num`) alone - the real backend has no per-entry timestamp
 * and never attaches a human meaning to an errno (WEBSITE_PLAN.md §12/§8). `type` ("N"=no error/
 * placeholder slot, "E"=error, "W"=warning) is by design never shown as text; it only selects
 * `num`'s color via `data-err-type` + `html/style.css`'s `.history-entry[data-err-type]` rules
 * (green/yellow/red) - the same "controller/template sets a semantic value, CSS alone decides what
 * it looks like" contract §12 already uses for `data-apply-status`. A row's own worst type (across
 * its history) drives the same color on its visible counter, and is what "flagged" filters by.
 * @param {ErrcountGroup} group
 * @param {Record<string, {counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}>} errcount
 * @returns {HTMLElement}
 */
export function buildErrcountGroup(group, errcount) {
    const card = document.createElement("div");
    card.className = "card";

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
    const allButton = document.createElement("button");
    allButton.type = "button";
    allButton.className = "action-button";
    allButton.textContent = "Show all";
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
 * Builds a section's static shell (heading + description) directly into `mainEl`, plus an empty
 * group grid for a controller to populate. Returns the grid.
 * @param {Section} section
 * @param {HTMLElement} mainEl
 * @returns {HTMLElement}
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

    const grid = document.createElement("div");
    grid.className = "group-grid";
    mainEl.appendChild(grid);
    return grid;
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
