import { afterEach, describe, expect, it } from "vitest";
import {
    buildErrcountGroup,
    buildField,
    buildFieldGroupCard,
    buildNavDrawer,
    buildSectionShell,
    formatFieldValue,
} from "../js/templates.js";

/**
 * @template {Element} [T=HTMLElement]
 * @param {ParentNode} root
 * @param {string} selector
 * @returns {T}
 */
function mustQuery(root, selector) {
    const found = root.querySelector(selector);
    if (found === null) {
        throw new Error(`Expected to find "${selector}"`);
    }
    return /** @type {T} */ (found);
}

describe("formatFieldValue", () => {
    it("shows an em dash for undefined/null", () => {
        expect(formatFieldValue({ key: "x", label: "X", kind: "readonly" }, undefined)).toBe("—");
        expect(formatFieldValue({ key: "x", label: "X", kind: "readonly" }, null)).toBe("—");
    });

    it("masks a masked field regardless of the underlying value", () => {
        expect(formatFieldValue({ key: "PW", label: "Password", kind: "string", mask: true }, "hunter2")).toBe("••••••••");
    });

    it("resolves an enum value to its label", () => {
        const field = {
            key: "OperationMode",
            label: "Mode",
            kind: /** @type {const} */ ("enum"),
            options: [{ value: 5, label: "Red + Green + Blue" }],
        };
        expect(formatFieldValue(field, 5)).toBe("Red + Green + Blue");
        expect(formatFieldValue(field, 99)).toBe("99"); // no matching option - falls back to the raw value
    });

    it("formats a gmtimestruct field from its real structured shape, not a pre-formatted string", () => {
        // Real shape (src/sensortask_wozi.py's _gmtimestruct_to_dict()): {year, month, mday, hour,
        // minute, second, weekday} - never a string, unlike what the mock fixtures used to fake.
        const field = { key: "UtcTime", label: "UTC Time", kind: /** @type {const} */ ("readonly"), format: /** @type {const} */ ("gmtimestruct") };
        const value = { year: 2025, month: 8, mday: 2, hour: 8, minute: 4, second: 3, weekday: 6 };
        expect(formatFieldValue(field, value)).toBe("2025-08-02 08:04:03");
    });
});

describe("buildField", () => {
    /** @type {HTMLElement | undefined} */
    let container;

    afterEach(() => {
        container?.remove();
    });

    /**
     * @param {HTMLElement} el
     * @returns {HTMLElement}
     */
    function mount(el) {
        container = document.createElement("div");
        container.appendChild(el);
        document.body.appendChild(container);
        return container;
    }

    it("renders a non-editable field as a plain value span, never an input", () => {
        const el = mount(buildField({ key: "CO2", label: "CO2", unit: "ppm", kind: "readonly" }, 612, false));
        expect(el.querySelector("input")).toBeNull();
        expect(mustQuery(el, '[data-field-key="CO2"]').textContent).toBe("612");
    });

    // An editable number/string field has two ".field-description"-classed <p>s (the "Current
    // value: …" caption, then the hint text) - the hint is always the last one.
    /**
     * @param {HTMLElement} el
     * @returns {string | null}
     */
    function hintText(el) {
        const nodes = el.querySelectorAll(".field-description");
        return nodes[nodes.length - 1].textContent;
    }

    it("shows a min/max range hint for an editable number field", () => {
        const el = mount(buildField({ key: "MeasInt", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 }, 5, true));
        expect(hintText(el)).toContain("Valid values: 2 to 1800 s");
    });

    it("shows a length hint for an editable string field", () => {
        const el = mount(buildField({ key: "Hostname", label: "Hostname", kind: "string", minLength: 1, maxLength: 63 }, "wozi", true));
        expect(hintText(el)).toContain("Length: 1 to 63 characters");
    });

    it("shows each special value's meaning in the description", () => {
        const field = {
            key: "AmbPres",
            label: "Ambient Pressure",
            unit: "hPa",
            kind: /** @type {const} */ ("number"),
            min: 700,
            max: 1400,
            specialValues: [{ value: 0, meaning: "Compensation off / use Altitude" }],
        };
        const el = mount(buildField(field, 1013, true));
        expect(hintText(el)).toContain("0 = Compensation off / use Altitude");
    });

    it("renders an editable toggle that flips its own On/Off state with no network call", () => {
        const el = mount(buildField({ key: "SelfCal", label: "Self-Cal", kind: "toggle" }, true, true));
        const button = mustQuery(el, '[data-field-key="SelfCal"]');
        expect(button.getAttribute("aria-pressed")).toBe("true");
        expect(button.textContent).toBe("On");

        button.click();

        expect(button.getAttribute("aria-pressed")).toBe("false");
        expect(button.textContent).toBe("Off");
        expect(button.dataset.value).toBe("false");
    });

    it("renders an editable enum as a select with the current value pre-selected", () => {
        const field = {
            key: "SensingRange",
            label: "Sensing Range",
            kind: /** @type {const} */ ("enum"),
            options: [
                { value: 0, label: "375 lux" },
                { value: 1, label: "10,000 lux" },
            ],
        };
        const el = mount(buildField(field, 1, true));
        const select = /** @type {HTMLSelectElement} */ (mustQuery(el, '[data-field-key="SensingRange"]'));
        expect(select.value).toBe("1");
    });

    it("renders an editable composite field with one input per sub-field", () => {
        const field = {
            key: "lightCmdLED",
            label: "LED Flash",
            kind: /** @type {const} */ ("composite"),
            subFields: [
                { key: "r", label: "Red", kind: /** @type {const} */ ("number") },
                { key: "g", label: "Green", kind: /** @type {const} */ ("number") },
            ],
        };
        const el = mount(buildField(field, undefined, true));
        const grid = mustQuery(el, '[data-field-key="lightCmdLED"]');
        expect(grid.querySelectorAll("input")).toHaveLength(2);
        expect(mustQuery(grid, '[data-sub-field-key="r"]')).not.toBeNull();
    });

    it("renders an editable number field pre-filled via a current-value caption, not the input's value", () => {
        const el = mount(buildField({ key: "MeasInt", label: "Measurement Interval", unit: "s", kind: "number", min: 2, max: 1800 }, 5, true));
        const input = /** @type {HTMLInputElement} */ (mustQuery(el, '[data-field-key="MeasInt"]'));
        expect(input.value).toBe(""); // sparse-PUT convention: starts empty, not pre-filled with the current value
        expect(mustQuery(el, '[data-current-value-for="MeasInt"]').textContent).toContain("5");
    });
});

describe("buildFieldGroupCard", () => {
    it("adds an inert Apply button/result paragraph for a submit group - clicking it does nothing on its own", () => {
        const group = {
            key: "SCD30",
            label: "SCD30",
            submit: true,
            fields: [{ key: "MeasInt", label: "Measurement Interval", kind: /** @type {const} */ ("number"), min: 2, max: 1800 }],
        };
        const card = buildFieldGroupCard(group, { MeasInt: 5 });
        expect(card.dataset.groupKey).toBe("SCD30");
        const button = mustQuery(card, ".apply-button");
        expect(() => button.click()).not.toThrow();
        expect(card.dataset.applyStatus).toBeUndefined(); // no networked behavior wired by the template itself
    });

    it("omits the Apply button entirely for a read-only group", () => {
        const group = { key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", kind: /** @type {const} */ ("readonly") }] };
        const card = buildFieldGroupCard(group, { CO2: 600 });
        expect(card.querySelector(".apply-button")).toBeNull();
    });
});

describe("buildErrcountGroup", () => {
    /** @type {import("../js/definitions.js").ErrcountGroup} */
    const THREE_MODULE_GROUP = {
        key: "errcount",
        label: "Errors",
        kind: "errcount",
        modules: [
            { key: "SCD30", label: "SCD30" },
            { key: "SGP40", label: "SGP40" },
            { key: "BMP3XX", label: "BMP388" },
        ],
    };
    /** @type {Record<string, {counter: number, history?: {num: number, type: "N"|"E"|"W"}[]}>} */
    const THREE_MODULE_ERRCOUNT = {
        SCD30: { counter: 0, history: [{ num: 0, type: "N" }] },
        SGP40: { counter: 3, history: [{ num: 0, type: "N" }, { num: 5, type: "W" }] },
        BMP3XX: { counter: 12, history: [{ num: 0, type: "N" }, { num: 2, type: "E" }] },
    };

    it("wraps the rollup and module list in a card with the group's heading, like every other field group", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        expect(wrapper.classList.contains("card")).toBe(true);
        expect(mustQuery(wrapper, "h3").textContent).toBe("Errors");
    });

    it("starts fully collapsed to just the rollup - no module rows visible", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        expect(mustQuery(wrapper, ".errcount-module-list").classList.contains("hidden")).toBe(true);
        // Rows exist in the DOM (built once, filtered by toggling .hidden - see the "Show
        // flagged"/"Show all" tests below) but every one starts hidden until a filter is chosen.
        const wrappers = wrapper.querySelectorAll(".errcount-row-wrapper");
        expect(wrappers).toHaveLength(3);
        expect([...wrappers].every((el) => el.classList.contains("hidden"))).toBe(true);
    });

    it("rolls up how many modules have errors vs. warnings, by each module's worst history entry", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        expect(mustQuery(wrapper, '[data-rollup="errors"]').textContent).toBe("1 module with errors");
        expect(mustQuery(wrapper, '[data-rollup="warnings"]').textContent).toBe("1 module with warnings");
    });

    it('"Show flagged" reveals only modules whose worst entry is an error or warning', () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        mustQuery(wrapper, ".action-button").click(); // "Show flagged" is the first action-button
        expect(mustQuery(wrapper, ".errcount-module-list").classList.contains("hidden")).toBe(false);
        const visible = [...wrapper.querySelectorAll(".errcount-row-wrapper")].filter(
            (el) => !el.classList.contains("hidden"),
        );
        expect(visible).toHaveLength(2);
        expect(visible.map((el) => /** @type {HTMLElement} */ (el).dataset.worst).sort()).toEqual(["E", "W"]);
    });

    it('"Show all" reveals every module regardless of worst status', () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        const buttons = wrapper.querySelectorAll(".action-button");
        /** @type {HTMLElement} */ (buttons[1]).click(); // "Show all"
        const visible = [...wrapper.querySelectorAll(".errcount-row-wrapper")].filter(
            (el) => !el.classList.contains("hidden"),
        );
        expect(visible).toHaveLength(3);
    });

    it("shows a module's own counter and its full history immediately once revealed - no separate expand click", () => {
        const wrapper = buildErrcountGroup(THREE_MODULE_GROUP, THREE_MODULE_ERRCOUNT);
        mustQuery(wrapper, ".action-button").click(); // reveal via "Show flagged"
        const row = mustQuery(wrapper, '.errcount-row-wrapper[data-worst="E"] .errcount-row');
        expect(mustQuery(row, ".errcount-row-count").textContent).toBe("12");
        expect(row.dataset.hasErrors).toBe("true");

        const list = mustQuery(/** @type {HTMLElement} */ (row.parentElement), ".history-list");
        expect(list.classList.contains("hidden")).toBe(false);
        expect(list.querySelectorAll(".history-entry")).toHaveLength(2);
    });

    it("shows a placeholder message for a module with no history", () => {
        const group = { key: "errcount", label: "Errors", kind: /** @type {const} */ ("errcount"), modules: [{ key: "SGP40", label: "SGP40" }] };
        const wrapper = buildErrcountGroup(group, { SGP40: { counter: 0 } });
        mustQuery(wrapper, ".action-button").click();
        expect(mustQuery(wrapper, ".history-empty").textContent).toBe("No history recorded.");
    });

    it("renders each entry's raw errno, colored by type via data-err-type only - never the type itself as text", () => {
        // Real backend shape (src/print_log.py's get_log()): no per-entry timestamp exists, and
        // "type" is never meant to be shown as text - only to color "num" (project owner,
        // session 2 follow-up). html/style.css's .history-entry[data-err-type] rules pick the color.
        const group = { key: "errcount", label: "Errors", kind: /** @type {const} */ ("errcount"), modules: [{ key: "BMP3XX", label: "BMP388" }] };
        const errcount = {
            BMP3XX: {
                counter: 3,
                history: [
                    { num: 0, type: /** @type {const} */ ("N") },
                    { num: 3, type: /** @type {const} */ ("W") },
                    { num: 2, type: /** @type {const} */ ("E") },
                ],
            },
        };
        const wrapper = buildErrcountGroup(group, errcount);
        mustQuery(wrapper, ".action-button").click();
        const entries = wrapper.querySelectorAll(".history-entry");
        expect(entries).toHaveLength(3);
        expect(/** @type {HTMLElement} */ (entries[0]).dataset.errType).toBe("N");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[0]), ".history-entry-num").textContent).toBe("0");
        expect(/** @type {HTMLElement} */ (entries[1]).dataset.errType).toBe("W");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[1]), ".history-entry-num").textContent).toBe("3");
        expect(/** @type {HTMLElement} */ (entries[2]).dataset.errType).toBe("E");
        expect(mustQuery(/** @type {HTMLElement} */ (entries[2]), ".history-entry-num").textContent).toBe("2");
        // No individual history entry ever renders "N"/"E"/"W"/"error"/"warning" as visible text
        // (the rollup line above them is allowed to say "errors"/"warnings" - only per-entry text is constrained).
        const list = mustQuery(wrapper, ".history-list");
        expect(list.textContent).not.toMatch(/error|warning|\bN\b|\bE\b|\bW\b/i);
    });
});

describe("buildSectionShell", () => {
    /** @type {HTMLElement | undefined} */
    let mainEl;

    afterEach(() => {
        mainEl?.remove();
    });

    it("builds the heading/description and returns an empty grid plus a hidden error banner, clearing prior content", () => {
        mainEl = document.createElement("main");
        mainEl.innerHTML = "<p>stale content from a previous section</p>";
        document.body.appendChild(mainEl);

        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "measurements",
            label: "Measurements",
            description: "Live readings.",
            rest: { get: "/measurements" },
            pollGroup: "live",
            groups: [],
        };
        const { grid, errorBanner } = buildSectionShell(section, mainEl);

        expect(mustQuery(mainEl, ".section-heading").textContent).toBe("Measurements");
        expect(mustQuery(mainEl, ".section-description").textContent).toBe("Live readings.");
        expect(grid.className).toBe("group-grid");
        expect(grid.children).toHaveLength(0);
        expect(mainEl.textContent).not.toContain("stale content");
        expect(errorBanner.classList.contains("hidden")).toBe(true);
        expect(errorBanner.classList.contains("error-banner")).toBe(true);
    });
});

describe("buildNavDrawer", () => {
    /** @type {HTMLElement | undefined} */
    let drawerEl;

    afterEach(() => {
        drawerEl?.remove();
    });

    it("builds one inert data-section-key link per section plus a device-name heading", () => {
        drawerEl = document.createElement("nav");
        document.body.appendChild(drawerEl);
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defs = {
            schemaVersion: "1.0.0",
            device: { id: "wozi", displayName: "wozi" },
            landingSection: "measurements",
            defaultPollIntervalMs: 3000,
            sections: [
                { key: "measurements", label: "Measurements", rest: { get: "/measurements" }, pollGroup: "live", groups: [] },
                { key: "sensors", label: "Sensors", rest: { get: "/sensors" }, pollGroup: "settings", groups: [] },
            ],
        };

        buildNavDrawer(defs, drawerEl);

        expect(mustQuery(drawerEl, ".nav-drawer-heading").textContent).toBe("wozi");
        const links = /** @type {NodeListOf<HTMLElement>} */ (drawerEl.querySelectorAll("[data-section-key]"));
        expect(links).toHaveLength(2);
        expect(links[0].dataset.sectionKey).toBe("measurements");
        // No listener attached yet - clicking must not throw and must have no observable effect.
        expect(() => links[0].click()).not.toThrow();
    });
});

describe("XSS safety (standing guideline: textContent only, never innerHTML)", () => {
    /** @type {HTMLElement | undefined} */
    let container;

    afterEach(() => {
        container?.remove();
    });

    const HOSTILE = '<img src=x onerror="window.__xssFired = true">';

    it("renders a hostile field label/value as literal text, never as parsed markup", () => {
        container = document.createElement("div");
        document.body.appendChild(container);

        /** @type {import("../js/definitions.js").FieldDef} */
        const field = { key: "CO2", label: HOSTILE, kind: "readonly" };
        container.appendChild(buildField(field, HOSTILE, false));

        expect(container.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(container.textContent).toContain(HOSTILE);
    });

    it("renders a hostile field-group label as literal text", () => {
        container = document.createElement("div");
        document.body.appendChild(container);

        /** @type {import("../js/definitions.js").FieldGroup} */
        const group = { key: "SCD30", label: HOSTILE, fields: [] };
        container.appendChild(buildFieldGroupCard(group, {}));

        expect(container.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(mustQuery(container, "h3").textContent).toBe(HOSTILE);
    });

    it("renders a hostile errcount module label as literal text", () => {
        container = document.createElement("div");
        document.body.appendChild(container);

        /** @type {import("../js/definitions.js").ErrcountGroup} */
        const group = { key: "errcount", label: "Errors", kind: "errcount", modules: [{ key: "SCD30", label: HOSTILE }] };
        container.appendChild(buildErrcountGroup(group, { SCD30: { counter: 0 } }));

        expect(container.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(container.textContent).toContain(HOSTILE);
    });

    it("renders a hostile device/section name in the nav drawer as literal text", () => {
        container = document.createElement("nav");
        document.body.appendChild(container);

        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defs = {
            schemaVersion: "1.0.0",
            device: { id: "x", displayName: HOSTILE },
            landingSection: "measurements",
            defaultPollIntervalMs: 3000,
            sections: [{ key: "measurements", label: HOSTILE, rest: { get: "/measurements" }, pollGroup: "live", groups: [] }],
        };

        buildNavDrawer(defs, container);

        expect(container.querySelector("img")).toBeNull();
        expect(/** @type {any} */ (window).__xssFired).toBeUndefined();
        expect(container.textContent).toContain(HOSTILE);
    });
});
