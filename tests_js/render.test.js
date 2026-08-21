import { afterEach, describe, expect, it } from "vitest";
import { installMockFetch } from "../js/mock-server.js";
import { renderSection } from "../js/render.js";

/**
 * Polls `check` until it returns a truthy value, instead of a fixed sleep - the mock server's
 * fetch has a randomized 80-200ms artificial latency per call (js/mock-server.js), and some
 * flows chain two calls (PUT then a refresh GET), so a fixed wait would either be flaky or
 * needlessly slow.
 * @param {() => unknown} check
 * @param {number} [timeoutMs]
 */
async function waitFor(check, timeoutMs = 2000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (check()) {
            return;
        }
        await new Promise((resolve) => setTimeout(resolve, 10));
    }
    throw new Error("waitFor timed out");
}

/**
 * querySelector with a runtime + type assertion that the element exists, so tests can chain
 * straight into `.value`/`.click()`/`.dataset` without every call site null-checking.
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

/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {
    schemaVersion: "1.0.0",
    device: { id: "test", displayName: "test" },
    landingSection: "measurements",
    defaultPollIntervalMs: 20,
    sections: [
        {
            key: "measurements",
            label: "Measurements",
            rest: { get: "/measurements" },
            pollGroup: "live",
            groups: [{ key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", unit: "ppm", kind: "readonly" }] }],
        },
        {
            key: "sensors",
            label: "Sensors",
            rest: { get: "/sensors", put: "/sensors" },
            pollGroup: "settings",
            groups: [
                {
                    key: "SCD30",
                    label: "SCD30",
                    submit: true,
                    fields: [
                        { key: "MeasInt", label: "Measurement Interval", kind: "number", min: 2, max: 1800 },
                        { key: "ContMeas", label: "Continuous Measurement", kind: "toggle", onLabel: "On", offLabel: "Off" },
                        {
                            key: "Oversampling",
                            label: "Oversampling",
                            kind: "enum",
                            options: [
                                { value: 1, label: "×1" },
                                { value: 4, label: "×4" },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            key: "status",
            label: "Status",
            rest: { get: "/status", put: "/status" },
            pollGroup: "settings",
            groups: [
                {
                    key: "errcount",
                    label: "Errors",
                    kind: "errcount",
                    modules: [{ key: "SCD30", label: "SCD30" }],
                },
            ],
        },
        {
            key: "notification",
            label: "Notification",
            rest: { get: "/notification", put: "/notification" },
            pollGroup: "settings",
            groups: [
                {
                    key: "flash",
                    label: "Manual Flash Command",
                    submit: true,
                    submitLabel: "Flash LED",
                    fields: [
                        {
                            key: "lightCmdLED",
                            label: "LED Flash",
                            kind: "composite",
                            subFields: [
                                { key: "r", label: "Red", kind: "number", min: 0, max: 255 },
                                { key: "g", label: "Green", kind: "number", min: 0, max: 255 },
                                { key: "b", label: "Blue", kind: "number", min: 0, max: 255 },
                                { key: "t", label: "Time (s)", kind: "number", min: 0.5, max: 60.0 },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
};

/** @param {string} key */
function getSection(key) {
    const section = DEFS.sections.find((s) => s.key === key);
    if (section === undefined) {
        throw new Error(`No section "${key}" in the test fixture`);
    }
    return section;
}

const DATA = {
    measurements: { SCD30: { CO2: 600 } },
    sensorsConfig: { SCD30: { MeasInt: 5, ContMeas: true, Oversampling: 1 } },
    networkingConfig: {},
    systemConfig: {},
    notificationConfig: {},
    status: {
        networking: {},
        system: {},
        sensors: {},
        notification: {},
        errcount: {
            SCD30: {
                counter: 2,
                history: [
                    { num: 2, type: /** @type {const} */ ("E") },
                    { num: 2, type: /** @type {const} */ ("E") },
                ],
            },
        },
    },
};

describe("renderSection", () => {
    /** @type {(() => void) | undefined} */
    let uninstall;
    /** @type {HTMLElement | undefined} */
    let mainEl;
    /** @type {(() => void) | undefined} */
    let stop;

    afterEach(() => {
        stop?.();
        uninstall?.();
        mainEl?.remove();
    });

    /** @returns {HTMLElement} */
    function mount() {
        mainEl = document.createElement("main");
        document.body.appendChild(mainEl);
        return mainEl;
    }

    it("renders readonly measurement fields and updates them on poll", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        // The mock server jitters every numeric measurement leaf on each GET (js/mock-server.js),
        // so the rendered value moves slightly away from the fixture's 600 rather than matching
        // it exactly - assert it arrived and is in the jitter's plausible neighborhood instead.
        await waitFor(() => main.querySelector('[data-field-key="CO2"]')?.textContent !== undefined);

        const value = mustQuery(main, '[data-field-key="CO2"]');
        expect(Number(value.textContent)).toBeGreaterThan(590);
        expect(Number(value.textContent)).toBeLessThan(610);
    });

    it("renders a writable number field pre-filled via its current-value caption, and a toggle button", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);

        await waitFor(() => main.querySelector('[data-current-value-for="MeasInt"]') !== null);

        const caption = mustQuery(main, '[data-current-value-for="MeasInt"]');
        expect(caption.textContent).toContain("5");

        const toggle = mustQuery(main, '[data-field-key="ContMeas"]');
        expect(toggle.getAttribute("aria-pressed")).toBe("true");
        expect(toggle.textContent).toBe("On");
    });

    it("submits an edited field via Apply and shows the resulting per-field status", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "3000"; // out of range (max 1800)
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("MeasInt: Invalid");
    });

    it("submits a numeric-valued enum field as a number, not a stringified one (regression)", async () => {
        // A <select>'s DOM .value is always a string, even for an option whose real value is a
        // number (e.g. BMP3XX's PressOvers). render.js must coerce it back before PUTing, and
        // mock-server.js must validate without forcing a string compare - otherwise every numeric
        // enum PUT reads back "Invalid" no matter what the visitor picked.
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="Oversampling"]') !== null);

        const select = /** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="Oversampling"]'));
        select.value = "4"; // the DOM always stores/reads select values as strings
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("Oversampling: Valid");
    });

    it("renders an errcount rollup, revealed via 'Show flagged', showing its full history immediately with no pagination", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("status"), main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        // Collapsed by default - only the rollup, no module row visible, until a filter is chosen.
        expect(main.querySelector(".errcount-module-list")?.classList.contains("hidden")).toBe(true);
        mustQuery(main, ".action-button").click(); // "Show flagged"

        const row = mustQuery(main, ".errcount-row");
        expect(mustQuery(row, ".errcount-row-count").textContent).toBe("2");

        // The revealed row's history is visible right away - no separate per-row expand click.
        const list = mustQuery(/** @type {HTMLElement} */ (row.parentElement), ".history-list");
        expect(list.classList.contains("hidden")).toBe(false);
        expect(list.querySelectorAll(".history-entry")).toHaveLength(2);
    });

    it("shows a visible error banner (without clearing existing data) when a live poll's GET fails, and hides it again once the next poll succeeds", async () => {
        const controls = { nextFailure: /** @type {"network" | number | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
        const banner = mustQuery(main, ".error-banner");
        expect(banner.classList.contains("hidden")).toBe(true);

        controls.nextFailure = 500;
        await waitFor(() => !banner.classList.contains("hidden"));
        expect(banner.textContent).toMatch(/measurements/i);
        // Stale data from before the failure is still on screen, not wiped out.
        expect(main.querySelector('[data-field-key="CO2"]')).not.toBeNull();

        await waitFor(() => banner.classList.contains("hidden"), 5000);
    });

    it("shows a visible error banner when a settings section's one-shot GET fails", async () => {
        const controls = { nextFailure: /** @type {"network" | number | undefined} */ ("network") };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/sensors/i);
    });

    it("reports Invalid for a composite field submitted with only some subfields filled", async () => {
        // collectGroupBody() only sends subfields the visitor actually filled in (render.js); the
        // real backend/mock-server then requires every subField present and valid, so a partial
        // submit must read back Invalid rather than silently applying a half-specified command.
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="lightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="lightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="r"]')).value = "100";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="g"]')).value = "50";
        // b and t left blank on purpose.
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("lightCmdLED: Invalid");
    });

    it("flattens per-sensor maintenance data one level for the Status section's sensors group", async () => {
        // groupValuesFrom() special-cases section "status" + group key "sensors": /status's
        // per-sensor maintenance sub-objects ({"SGP40": {BackupTS, RestoreTS}}) get flattened to
        // "SGP40_BackupTS" so field keys can address them directly, matching every other group's
        // already-flat convention.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithMaintenance = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "status"),
                {
                    key: "status",
                    label: "Status",
                    rest: { get: "/status" },
                    pollGroup: "settings",
                    groups: [{ key: "sensors", label: "Maintenance", fields: [{ key: "SGP40_BackupTS", label: "SGP40 Backup", kind: "readonly" }] }],
                },
            ],
        };
        const dataWithMaintenance = {
            ...DATA,
            status: { ...DATA.status, sensors: { SGP40: { BackupTS: 12345 } } },
        };
        uninstall = installMockFetch(defsWithMaintenance, dataWithMaintenance);
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithMaintenance.sections.find((s) => s.key === "status"));
        stop = renderSection(defsWithMaintenance, section, main);

        await waitFor(() => main.querySelector('[data-field-key="SGP40_BackupTS"]') !== null);
        expect(mustQuery(main, '[data-field-key="SGP40_BackupTS"]').textContent).toBe("12345");
    });

    it("shows 'Request failed' and a failed apply-status when the PUT itself fails (network failure)", async () => {
        const controls = { nextFailure: /** @type {"network" | number | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "10";
        controls.nextFailure = "network";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/request failed/i);
        // The Apply button is re-enabled afterward, not left permanently stuck.
        expect(/** @type {HTMLButtonElement} */ (mustQuery(main, ".apply-button")).disabled).toBe(false);
    });
});
