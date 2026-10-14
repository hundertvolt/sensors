import { afterEach, describe, expect, it, vi } from "vitest";
import { installMockFetch } from "../js/mock-server.js";
import { hideBanner, renderSection, showBanner } from "../js/render.js";
import { mustQuery } from "./_dom_helpers.js";

// @tunable l0.render_wait_timeout_ms = 2000
const WAIT_TIMEOUT_MS = 2000;
// @tunable l0.render_poll_ms = 10
const WAIT_POLL_MS = 10;
// @tunable l0.render_banner_wait_ms = 5000
const BANNER_WAIT_MS = 5000;

// Polls `check` instead of a fixed sleep: some flows chain two requests, so a fixed wait would be flaky or slow.
/**
 * @param {() => unknown} check
 * @param {number} [timeoutMs]
 */
async function waitFor(check, timeoutMs = WAIT_TIMEOUT_MS) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (check()) {
            return;
        }
        // eslint-disable-next-line no-await-in-loop -- each retry waits out the previous delay before rechecking
        await new Promise((resolve) => {
            setTimeout(resolve, WAIT_POLL_MS);
        });
    }
    throw new Error("waitFor timed out");
}

/**
 * Wraps the fetch installed now and logs every request it sees as "<METHOD> <url>", oldest first.
 * @returns {string[]}
 */
function recordRequests() {
    /** @type {string[]} */
    const log = [];
    const inner = window.fetch;
    window.fetch = (input, init) => {
        log.push(`${init?.method ?? "GET"} ${String(input)}`);
        return inner(input, init);
    };
    return log;
}

/**
 * Answers a GET of each listed URL with its next body as JSON (the last one repeats); every other
 * request reaches the fetch installed now.
 * @param {Record<string, unknown[]>} bodies
 */
function answerGets(bodies) {
    const inner = window.fetch;
    window.fetch = (input, init) => {
        const answers = bodies[String(input)];
        if ((init?.method ?? "GET") === "GET" && answers !== undefined) {
            const body = answers.length > 1 ? answers.shift() : answers[0];
            return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
        }
        return inner(input, init);
    };
}

/**
 * Wraps the fetch installed now and keeps every PUT body it sees as parsed JSON, oldest first.
 * @returns {unknown[]}
 */
function capturePutBodies() {
    /** @type {unknown[]} */
    const bodies = [];
    const inner = window.fetch;
    window.fetch = (input, init) => {
        if (init?.method === "PUT") {
            bodies.push(JSON.parse(String(init.body)));
        }
        return inner(input, init);
    };
    return bodies;
}

/**
 * Answers every PUT of `url` with `result` in a "Command executed" envelope; every other request reaches
 * the fetch installed now.
 * @param {string} url
 * @param {unknown} result
 */
function answerPuts(url, result) {
    const inner = window.fetch;
    window.fetch = (input, init) => {
        if (String(input) === url && init?.method === "PUT") {
            const envelope = { res: "OK", code: 0, descr: "Command executed", result };
            return Promise.resolve(new Response(JSON.stringify(envelope), { status: 200 }));
        }
        return inner(input, init);
    };
}

/**
 * Arms the mock's one-shot failure for the next PUT only, so the GET an Apply sends first still answers.
 * @param {import("../js/mock-server.js").MockFetchControls} controls
 * @param {import("../js/mock-server.js").MockFailure} failure
 */
function failNextPut(controls, failure) {
    const inner = window.fetch;
    let armed = true;
    window.fetch = (input, init) => {
        if (armed && init?.method === "PUT") {
            armed = false;
            controls.nextFailure = failure;
        }
        return inner(input, init);
    };
}

/**
 * Clicks the card's Apply and waits until the button is enabled again: the PUT, its results and the
 * post-write GET are done.
 * @param {HTMLElement} card
 */
async function applyAndSettle(card) {
    const button = /** @type {HTMLButtonElement} */ (mustQuery(card, ".apply-button"));
    button.click();
    await waitFor(() => !button.disabled);
}

/**
 * Types `text` into an input as a visitor would: the value, then the input event.
 * @param {HTMLInputElement} input
 * @param {string} text
 */
function typeInto(input, text) {
    input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
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
            groups: [
                { key: "SCD30", label: "SCD30", fields: [{ key: "CO2", label: "CO2", unit: "ppm", kind: "readonly" }] },
                {
                    // A nested, precision-declared measurement group - the shape the ISL29125's
                    // own body introduced (SPECIFICATION.md Part H.5's `path`/`decimals` hints).
                    key: "COLOUR",
                    label: "Colour",
                    fields: [
                        { key: "Lux", label: "Illuminance", unit: "lx", kind: "readonly", decimals: 2 },
                        { key: "R", label: "Red", kind: "readonly", path: ["RGB", "R"], decimals: 4 },
                        { key: "Bri", label: "Brightness", kind: "readonly", path: ["HSB", "B"], decimals: 4 },
                        { key: "CCT", label: "Colour Temperature", unit: "K", kind: "readonly", decimals: 0 },
                    ],
                },
            ],
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
                        { key: "MeasInterval", label: "Measurement Interval", kind: "number", min: 2, max: 1800 },
                        // min: 0 deliberately, to catch a form input coerced to the number 0 by
                        // accident (e.g. non-numeric text) rather than one genuinely submitted as 0.
                        { key: "COffset", label: "Calibration Offset", kind: "number", min: 0, max: 500 },
                        // A plain toggle: no dispatch or alwaysExecuted flag, so the mock stores and echoes it (SPECIFICATION.md Part H.4).
                        { key: "MeasEnabled", label: "Continuous Measurement", kind: "toggle", onLabel: "On", offLabel: "Off" },
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
                            key: "LightCmdLED",
                            label: "LED Flash",
                            kind: "composite",
                            subFields: [
                                { key: "R", label: "Red", kind: "number", min: 0, max: 255 },
                                { key: "G", label: "Green", kind: "number", min: 0, max: 255 },
                                { key: "B", label: "Blue", kind: "number", min: 0, max: 255 },
                                { key: "T", label: "Time (s)", kind: "number", min: 0.5, max: 60.0 },
                            ],
                        },
                    ],
                },
                {
                    key: "pause",
                    label: "Pause Notifications",
                    submit: true,
                    fields: [{ key: "PauseTime", label: "Pause Time", unit: "s", kind: "number", min: 0, max: 86400, statusPath: ["notification", "PauseTime"] }],
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

/**
 * The fixture's definitions with `section` in place of its namesake.
 * @param {import("../js/definitions.js").Section} section
 * @returns {import("../js/definitions.js").SiteDefinitions}
 */
function withSection(section) {
    return { ...DEFS, sections: [...DEFS.sections.filter((s) => s.key !== section.key), section] };
}

/** @type {import("../js/definitions.js").Section} */
const RESET_SECTION = {
    key: "status",
    label: "Status",
    rest: { get: "/status", put: "/status" },
    pollGroup: "settings",
    groups: [
        {
            key: "resetErrors",
            label: "Reset Errors",
            submit: true,
            submitLabel: "Reset All Errors",
            fields: [{ key: "ResetErrors", label: "Confirm Reset", kind: "toggle", onLabel: "Yes, reset", offLabel: "No", dispatch: true, confirm: true }],
        },
    ],
};

/** @type {import("../js/definitions.js").Section} */
const SYSTEM_SECTION = {
    key: "system",
    label: "System",
    rest: { get: "/system", put: "/system" },
    pollGroup: "settings",
    groups: [
        {
            key: "command",
            label: "System Command",
            submit: true,
            fields: [
                {
                    key: "SystemCmd",
                    label: "Command",
                    kind: "enum",
                    dispatch: true,
                    confirm: true,
                    options: [
                        { value: "reboot", label: "Reboot" },
                        { value: "bootloader", label: "Reboot into bootloader" },
                        { value: "mempause", label: "Pause backups for 5 minutes" },
                        { value: "resetconfig", label: "Reset to defaults" },
                        { value: "erasefram", label: "Erase FRAM" },
                    ],
                },
            ],
        },
    ],
};

const DATA = {
    measurements: {
        SCD30: { CO2: 600 },
        // A lit scene, and a coherent one: HSB.B is max(R, G, B) as the real driver computes it.
        COLOUR: { Lux: 337.4219, RGB: { R: 0.2814159, G: 0.6337, B: 0.151 }, HSB: { H: 78.4, S: 0.552, B: 0.6337 }, CCT: null },
    },
    sensorsConfig: { SCD30: { MeasInterval: 5, COffset: 10, MeasEnabled: true, Oversampling: 1 } },
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

describe("showBanner and hideBanner", () => {
    it("show the message through data-shown, and hide it keeping the text", () => {
        const el = document.createElement("p");
        showBanner(el, "Could not refresh Sensors: boom");
        expect(el.textContent).toBe("Could not refresh Sensors: boom");
        expect(el.dataset.shown).toBe("true");

        hideBanner(el);
        expect(el.dataset.shown).toBe("false");
        expect(el.textContent).toBe("Could not refresh Sensors: boom");
    });
});

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

    it("renders a nested measurement field's own leaf at its declared precision, not [object Object]", async () => {
        // The full path the ISL29125 introduced: definitions.js walks field.path, field-format.js
        // applies field.decimals, templates.js renders it. Randomness pinned to its midpoint is
        // exactly zero jitter, so a leaf below 1 reaches the card at its own declared precision.
        const random = vi.spyOn(Math, "random").mockReturnValue(0.5);
        try {
            uninstall = installMockFetch(DEFS, DATA);
            const main = mount();
            stop = renderSection(DEFS, getSection("measurements"), main);

            await waitFor(() => main.querySelector('[data-field-key="R"]') !== null);

            const red = mustQuery(main, '[data-field-key="R"]').textContent ?? "";
            expect(red).not.toContain("object");
            expect(red).toBe("0.2814"); // the fixture's own value, at the field's own decimals: 4
            const brightness = mustQuery(main, '[data-field-key="Bri"]').textContent ?? "";
            // RGB.B (0.151) and HSB.B (0.6337) are different values under the same leaf name -
            // which is the whole reason the measurement body is nested rather than flattened.
            // Resolving the path wrongly would render either 0.1500 or the red above.
            expect(brightness).toBe("0.6337");
            expect(brightness).not.toBe(red);
            expect(mustQuery(main, '[data-field-key="Lux"]').textContent).toBe("337.42");
            // A null CCT (a dark room) stays an em dash rather than becoming "null" or 0.
            expect(mustQuery(main, '[data-field-key="CCT"]').textContent).toBe("\u2014");
        } finally {
            random.mockRestore();
        }
    });

    it("renders a writable number field pre-filled via its current-value caption, and a toggle button", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);

        await waitFor(() => main.querySelector('[data-current-value-for="MeasInterval"]') !== null);

        const caption = mustQuery(main, '[data-current-value-for="MeasInterval"]');
        expect(caption.textContent).toContain("5");

        const toggle = mustQuery(main, '[data-field-key="MeasEnabled"]');
        expect(toggle.getAttribute("aria-pressed")).toBe("true");
        expect(toggle.textContent).toBe("On");
    });

    it("submits an edited field via Apply and shows the resulting per-field status", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]'));
        input.value = "3000"; // out of range (max 1800)
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("MeasInterval: Invalid");
        // The field's own box carries its own result too, not just the card-level worst status
        // (legacy per-field granularity, restored alongside the new accent-stripe presentation).
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("invalid");
    });

    it("colors each individual field's own box by its own result, not just the card's worst status", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]')).value = "3000"; // out of range
        // COffset and MeasEnabled are left untouched on purpose: the sparse-PUT convention omits
        // a blank number input, and collectGroupBody() omits a non-dispatch toggle or enum the
        // same way once it matches its current value.
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid"); // worst-first across the whole group

        expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("invalid");
        // Neither COffset nor MeasEnabled was part of this submission at all (both sparse-omitted) -
        // no per-field result to show, matching the legacy behavior this restores: only fields
        // present in the response's own result get colored.
        expect(mustQuery(card, '[data-field-wrapper-key="MeasEnabled"]').dataset.applyStatus).toBeUndefined();
        expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBeUndefined();
    });

    it("sparse-omits an untouched toggle/enum field left at its current value, unlike a dispatch-marked field", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasEnabled"]') !== null);

        // MeasEnabled/Oversampling both start at their real current value (DATA.sensorsConfig.SCD30)
        // and are never touched - only MeasInterval is genuinely changed.
        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]')).value = "10";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("valid");
        // Only the field that actually changed shows up in the result text.
        expect(mustQuery(card, ".apply-result").textContent).toBe("Command executed — MeasInterval: Valid");
    });

    it("still submits a toggle/enum field explicitly flipped back to its original value (a real, deliberate change)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasEnabled"]') !== null);

        const toggle = mustQuery(main, '[data-field-key="MeasEnabled"]');
        toggle.click(); // On -> Off: a real, deliberate change from the current value (true)
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("MeasEnabled: Valid");
    });

    it("submits a numeric-valued enum field as a number, not a stringified one (regression)", async () => {
        // A <select>'s DOM .value is always a string, even where the real value is a number
        // (BMP3XX's PresOvers). render.js must coerce it back before PUTing and mock-server.js
        // must not force a string compare, or every numeric enum PUT reads back "Invalid".
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

    it("renders an errcount group outside the Status section from GET /status's errcount", async () => {
        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [{ key: "dnsErrors", label: "Captive DNS Error History", kind: "errcount", modules: [{ key: "DNSSRV", label: "Captive DNS" }] }],
        };
        const defs = { ...DEFS, sections: [...DEFS.sections, section] };
        const dnsHistory = [{ num: 3, type: /** @type {const} */ ("W") }];
        uninstall = installMockFetch(defs, { ...DATA, status: { ...DATA.status, errcount: { ...DATA.status.errcount, DNSSRV: { counter: 1, history: dnsHistory } } } });
        const main = mount();
        stop = renderSection(defs, section, main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        mustQuery(main, ".action-button").click(); // "Show flagged"
        expect(mustQuery(main, ".errcount-row-name").textContent).toBe("Captive DNS");
        expect(mustQuery(mustQuery(main, ".errcount-row"), ".errcount-row-count").textContent).toBe("1");
    });

    it("preserves an expanded errcount card's 'Show flagged'/'Show all' state across a live poll update", async () => {
        // Every real device's Status section is live and this fixture's is not, so the poll-update path needs a local variant.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithLiveErrcount = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "status"),
                { ...getSection("status"), pollGroup: "live", pollIntervalMs: 50 },
            ],
        };
        uninstall = installMockFetch(defsWithLiveErrcount, DATA);
        const requests = recordRequests();
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithLiveErrcount.sections.find((s) => s.key === "status"));
        stop = renderSection(defsWithLiveErrcount, section, main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        mustQuery(main, '[data-errcount-action="flagged"]').click();
        expect(mustQuery(main, ".errcount-module-list").classList.contains("hidden")).toBe(false);

        // Two more GETs: a poll update really ran, which a timer armed before fake timers never would.
        const seen = requests.length;
        await waitFor(() => requests.length >= seen + 2);

        // The poll update keeps the chosen filter.
        expect(mustQuery(main, ".errcount-module-list").classList.contains("hidden")).toBe(false);
        expect(mustQuery(main, ".errcount-row").textContent).toContain("2");
    });

    it("shows Valid after a successful Reset All Errors submission, read from /status's per-field result", async () => {
        const defs = withSection(RESET_SECTION);
        uninstall = installMockFetch(defs, DATA);
        const puts = capturePutBodies();
        const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
        const main = mount();
        stop = renderSection(defs, RESET_SECTION, main);
        await waitFor(() => main.querySelector('[data-field-key="ResetErrors"]') !== null);

        mustQuery(main, '[data-field-key="ResetErrors"]').click(); // flips the toggle to "Yes, reset"
        const card = mustQuery(main, '[data-group-key="resetErrors"]');
        await applyAndSettle(card);

        expect(confirm.mock.calls).toEqual([["Reset All Errors?"]]);
        expect(puts).toEqual([{ ResetErrors: true }]);
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toBe("Command executed — ResetErrors: Valid");
        expect(mustQuery(card, '[data-field-wrapper-key="ResetErrors"]').dataset.applyStatus).toBe("valid");

        // The toggle is Off after the first Apply, so a second click has nothing to submit.
        expect(mustQuery(main, '[data-field-key="ResetErrors"]').dataset.value).toBe("false");
        await applyAndSettle(card);
        expect(mustQuery(card, ".apply-result").textContent).toBe("Nothing to submit - no fields were changed.");
        expect(puts).toHaveLength(1);
    });

    it("shows Failed when /status's PUT answers the reset Failed", async () => {
        const defs = withSection(RESET_SECTION);
        uninstall = installMockFetch(defs, DATA);
        answerPuts("/status", { ResetErrors: "Failed" });
        vi.spyOn(window, "confirm").mockReturnValue(true);
        const main = mount();
        stop = renderSection(defs, RESET_SECTION, main);
        await waitFor(() => main.querySelector('[data-field-key="ResetErrors"]') !== null);

        mustQuery(main, '[data-field-key="ResetErrors"]').click();
        const card = mustQuery(main, '[data-group-key="resetErrors"]');
        await applyAndSettle(card);

        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, '[data-field-wrapper-key="ResetErrors"]').dataset.applyStatus).toBe("failed");
    });

    it("sends no reset when its confirmation is declined, and leaves the toggle as set", async () => {
        const defs = withSection(RESET_SECTION);
        uninstall = installMockFetch(defs, DATA);
        const puts = capturePutBodies();
        const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
        const main = mount();
        stop = renderSection(defs, RESET_SECTION, main);
        await waitFor(() => main.querySelector('[data-field-key="ResetErrors"]') !== null);

        mustQuery(main, '[data-field-key="ResetErrors"]').click();
        const card = mustQuery(main, '[data-group-key="resetErrors"]');
        await applyAndSettle(card);

        expect(confirm).toHaveBeenCalledWith("Reset All Errors?");
        expect(puts).toEqual([]);
        expect(card.dataset.applyStatus).toBeUndefined();
        expect(mustQuery(main, '[data-field-key="ResetErrors"]').dataset.value).toBe("true");
    });

    describe("an always-executed toggle with no GET value", () => {
        // Shaped like the real ContMeas (SPECIFICATION.md Part H.5): GET never reports it, the device runs it on every write.
        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [
                {
                    key: "aux",
                    label: "Auxiliary",
                    submit: true,
                    fields: [{ key: "AuxEnabled", label: "Auxiliary Output", kind: "toggle", onLabel: "On", offLabel: "Off", alwaysExecuted: true }],
                },
            ],
        };
        const defs = withSection(section);
        // networkingConfig never mentions AuxEnabled, so the mock's GET omits it as the device's omits ContMeas.
        const dataWithoutReadback = { ...DATA, networkingConfig: {} };

        it("renders unset, and an untouched Apply has nothing to submit", async () => {
            uninstall = installMockFetch(defs, dataWithoutReadback);
            const puts = capturePutBodies();
            const main = mount();
            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelector('[data-field-key="AuxEnabled"]') !== null);

            const toggle = mustQuery(main, '[data-field-key="AuxEnabled"]');
            expect(toggle.dataset.value).toBe("unset");
            expect(toggle.getAttribute("aria-pressed")).toBe("mixed");
            expect(toggle.textContent).toBe("\u2014");

            await applyAndSettle(mustQuery(main, '[data-group-key="aux"]'));
            expect(mustQuery(main, ".apply-result").textContent).toBe("Nothing to submit - no fields were changed.");
            expect(mustQuery(main, '[data-group-key="aux"]').dataset.applyStatus).toBeUndefined();
            expect(puts).toEqual([]);
        });

        it("sends false once set Off, then returns to unset after the Apply", async () => {
            uninstall = installMockFetch(defs, dataWithoutReadback);
            const puts = capturePutBodies();
            const main = mount();
            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelector('[data-field-key="AuxEnabled"]') !== null);

            const toggle = mustQuery(main, '[data-field-key="AuxEnabled"]');
            toggle.click(); // unset -> On
            toggle.click(); // On -> Off
            const card = mustQuery(main, '[data-group-key="aux"]');
            await applyAndSettle(card);

            expect(puts).toEqual([{ AuxEnabled: false }]);
            expect(mustQuery(card, ".apply-result").textContent).toContain("AuxEnabled: Valid");
            expect(mustQuery(main, '[data-field-key="AuxEnabled"]').dataset.value).toBe("unset");
        });
    });

    it("skips the PUT and shows a neutral message when Apply is clicked with nothing to submit", async () => {
        // A group of only number/string fields can be genuinely empty when the visitor clicks
        // Apply without touching anything, and collectGroupBody() then returns {}: no round trip.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsNumberOnly = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "networking"),
                {
                    key: "networking",
                    label: "Networking",
                    rest: { get: "/networking", put: "/networking" },
                    pollGroup: "settings",
                    groups: [
                        {
                            key: "identity",
                            label: "Wi-Fi & Identity",
                            submit: true,
                            fields: [{ key: "SSID", label: "Wi-Fi SSID", kind: "string", minLength: 2, maxLength: 32 }],
                        },
                    ],
                },
            ],
        };
        uninstall = installMockFetch(defsNumberOnly, DATA);
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsNumberOnly.sections.find((s) => s.key === "networking"));
        stop = renderSection(defsNumberOnly, section, main);
        await waitFor(() => main.querySelector('[data-field-key="SSID"]') !== null);

        // SSID left blank on purpose - nothing to submit.
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, ".apply-result").textContent !== "");

        const card = mustQuery(main, '[data-group-key="identity"]');
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/nothing to submit/i);
        // No PUT was sent, so there is no outcome to colour.
        expect(card.dataset.applyStatus).toBeUndefined();
    });

    it("skips the PUT for an enum-only submit group (e.g. SystemCmd) left untouched, instead of silently dispatching whichever command the browser defaults a bare <select> to (regression)", async () => {
        // SystemCmd is never returned by GET /system (SPECIFICATION.md A.8), so the select starts on its placeholder and an untouched Apply sends nothing.
        const defsSystemCmd = withSection(SYSTEM_SECTION);
        uninstall = installMockFetch(defsSystemCmd, DATA);
        // Layered on top of the mock's own fetch - afterEach's uninstall() call restores the true
        // original regardless of how many times window.fetch was reassigned in between, so no
        // manual restore is needed here.
        const mockedFetch = window.fetch;
        let putSent = false;
        window.fetch = (input, init) => {
            if (String(input) === "/system" && init?.method === "PUT") {
                putSent = true;
            }
            return mockedFetch(input, init);
        };

        const main = mount();
        stop = renderSection(defsSystemCmd, SYSTEM_SECTION, main);
        await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);

        const select = /** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="SystemCmd"]'));
        expect(select.value).toBe(""); // never silently defaults to a real command

        mustQuery(main, ".apply-button").click();
        await waitFor(() => mustQuery(main, ".apply-result").textContent !== "");

        expect(mustQuery(main, ".apply-result").textContent).toMatch(/nothing to submit/i);
        expect(putSent).toBe(false);
    });

    it("shows a visible error banner (without clearing existing data) when a live poll's GET fails, and hides it again once the next poll succeeds", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        // A slower tick than the fixture's 20 ms, so the failed state lasts long enough to be seen.
        stop = renderSection(DEFS, { ...getSection("measurements"), pollIntervalMs: 200 }, main);

        await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
        const banner = mustQuery(main, ".error-banner");
        expect(banner.dataset.shown).toBe("false");

        controls.nextFailure = 500;
        await waitFor(() => banner.dataset.shown === "true");
        expect(banner.textContent).toMatch(/measurements/i);
        // The server's own shaped-error descr surfaces verbatim, not just a bare status code.
        expect(banner.textContent).toMatch(/internal server error/i);
        // Stale data from before the failure is still on screen, not wiped out.
        expect(main.querySelector('[data-field-key="CO2"]')).not.toBeNull();

        await waitFor(() => banner.dataset.shown === "false", BANNER_WAIT_MS);
    });

    it("shows a visible error banner when a settings section's one-shot GET fails, and a later tick recovers it", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("network") };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        // A slower retry than the fixture's 20 ms, so the failed state lasts long enough to be seen.
        stop = renderSection(DEFS, { ...getSection("sensors"), pollIntervalMs: 200 }, main);

        await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/sensors/i);
        expect(main.querySelector('[data-group-key="SCD30"]')).toBeNull();

        await waitFor(() => main.querySelector('[data-group-key="SCD30"]') !== null);
        expect(mustQuery(main, ".error-banner").dataset.shown).toBe("false");
    });

    it("reports Invalid for non-numeric text in a number field instead of silently submitting 0 (regression)", async () => {
        // JSON.stringify(NaN) is "null"; the raw text is sent instead so the server can refuse it.
        // COffset's min is 0 precisely so a min>0 rejection cannot pass this by accident.
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="COffset"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="COffset"]'));
        input.value = "abc";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("COffset: Invalid");
    });

    it("reports Invalid for non-numeric text in a composite subfield instead of silently submitting 0 (regression)", async () => {
        // The same NaN -> null -> 0 gap as the number-field case above, through
        // collectGroupBody()'s composite branch: r's min is 0, so garbage becoming 0 would pass.
        // A non-numeric member is refused by the dispatcher's per-member validation (SPECIFICATION.md A.8).
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="LightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="LightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="R"]')).value = "abc";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="G"]')).value = "50";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="B"]')).value = "50";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="T"]')).value = "1";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("LightCmdLED: Invalid");
    });

    it("reports Invalid for a composite field submitted with only some subfields filled", async () => {
        // collectGroupBody() sends only the subfields the visitor filled in; the dispatcher refuses a
        // payload missing a member as "Invalid", the answer to any malformed one (SPECIFICATION.md A.8).
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="LightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="LightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="R"]')).value = "100";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="G"]')).value = "50";
        // b and t left blank on purpose.
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("LightCmdLED: Invalid");
    });

    it("reports Valid for a fully-specified composite LightCmdLED submission and never persists it (dispatch-only, matches real GET /notification)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="LightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="LightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="R"]')).value = "10";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="G"]')).value = "20";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="B"]')).value = "30";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="T"]')).value = "1";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("LightCmdLED: Valid");
        // A command the device ran has its sub-inputs cleared, so a second click cannot re-send it.
        await waitFor(() => [...grid.querySelectorAll("input")].every((input) => input.value === ""));
    });

    it("skips the PUT and shows a neutral message when LightCmdLED's Apply is clicked with every subfield left blank", async () => {
        // The "flash" group holds only the composite LightCmdLED, which collectGroupBody() omits
        // entirely when no subfield was touched - the same sparse-PUT convention every other kind
        // follows. The composite instance of the "nothing to submit" path SSID and SystemCmd cover.
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="LightCmdLED"]') !== null);

        const card = mustQuery(main, '[data-group-key="flash"]');
        mustQuery(card, ".apply-button").click();

        await waitFor(() => mustQuery(card, ".apply-result").textContent !== "");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/nothing to submit/i);
        expect(card.dataset.applyStatus).toBeUndefined();
    });

    it("reads maintenance data by path, each of two instances whose flattened keys would collide showing its own value", async () => {
        // "SGP40" + "x_BackupTS" and "SGP40_x" + "BackupTS" flatten to one key; each path names its instance.
        /** @type {import("../js/definitions.js").Section} */
        const section = {
            key: "status",
            label: "Status",
            rest: { get: "/status" },
            pollGroup: "settings",
            groups: [
                {
                    key: "sensors",
                    label: "Maintenance",
                    fields: [
                        { key: "SGP40_BackupTS", label: "SGP40 Backup", kind: "readonly", path: ["SGP40", "BackupTS"] },
                        { key: "SGP40_x_BackupTS", label: "SGP40_x Backup", kind: "readonly", path: ["SGP40_x", "BackupTS"] },
                        { key: "SGP40_xBackupTS", label: "SGP40 x Backup", kind: "readonly", path: ["SGP40", "x_BackupTS"] },
                    ],
                },
            ],
        };
        const defs = { ...DEFS, sections: [...DEFS.sections.filter((s) => s.key !== "status"), section] };
        const data = { ...DATA, status: { ...DATA.status, sensors: { SGP40: { BackupTS: 12345, "x_BackupTS": 3 }, "SGP40_x": { BackupTS: 67890 } } } };
        uninstall = installMockFetch(defs, data);
        const main = mount();
        stop = renderSection(defs, section, main);

        await waitFor(() => main.querySelector('[data-field-key="SGP40_BackupTS"]')?.textContent === "12345");
        expect(mustQuery(main, '[data-field-key="SGP40_x_BackupTS"]').textContent).toBe("67890");
        expect(mustQuery(main, '[data-field-key="SGP40_xBackupTS"]').textContent).toBe("3");
    });

    it("shows a visible error banner when a GET response body is empty", async () => {
        const originalFetch = window.fetch;
        window.fetch = (input) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/measurements") {
                return Promise.resolve(new Response("", { status: 200 }));
            }
            return originalFetch(input);
        };
        uninstall = () => {
            window.fetch = originalFetch;
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/measurements/i);
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/empty body/i);
    });

    it("shows a clear, non-crashing error banner when a GET response body is torn/truncated JSON (a transmission error)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("torn-json") };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/measurements/i);
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/not valid json|corrupted|truncated/i);
    });

    it("surfaces the server's own descr text when a section's /status sub-request returns a shaped HTTP error", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const mockedFetch = window.fetch;
        window.fetch = (input, init) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/status") {
                return Promise.resolve(new Response(JSON.stringify({ res: "ERR", code: 404, descr: "Not found", result: {} }), { status: 404 }));
            }
            return mockedFetch(input, init);
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);

        await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/not found/i);
    });

    it("shows a visible error banner when a section's /status sub-request fails", async () => {
        // PauseTime's statusPath makes the section read GET /status after its own GET /notification;
        // a failure of that second request must surface too, not be swallowed.
        uninstall = installMockFetch(DEFS, DATA);
        const mockedFetch = window.fetch;
        window.fetch = (input, init) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/status") {
                return Promise.reject(new TypeError("Failed to fetch (simulated)"));
            }
            return mockedFetch(input, init);
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);

        await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/notification/i);
    });

    it("refreshes a readonly field embedded in a writable, live-polled group in place on the next poll", async () => {
        // No real definitions file nests a readonly field inside a submit:true group in a "live"
        // section today, but the renderer is schema-agnostic and must handle one, so this fixture
        // exercises that path.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithReadonlyInWritable = {
            ...DEFS,
            sections: [
                {
                    key: "measurements",
                    label: "Measurements",
                    rest: { get: "/measurements" },
                    pollGroup: "live",
                    pollIntervalMs: 200,
                    groups: [{ key: "SCD30", label: "SCD30", submit: true, fields: [{ key: "Model", label: "Model", kind: "readonly" }] }],
                },
                ...DEFS.sections.filter((s) => s.key !== "measurements"),
            ],
        };
        let callCount = 0;
        const originalFetch = window.fetch;
        window.fetch = (input) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/measurements") {
                callCount += 1;
                return Promise.resolve(new Response(JSON.stringify({ SCD30: { Model: callCount === 1 ? "B" : "A" } }), { status: 200 }));
            }
            return originalFetch(input);
        };
        uninstall = () => {
            window.fetch = originalFetch;
        };
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithReadonlyInWritable.sections.find((s) => s.key === "measurements"));
        stop = renderSection(defsWithReadonlyInWritable, section, main);

        await waitFor(() => main.querySelector('.field-value[data-field-key="Model"]')?.textContent === "B");
        const span = mustQuery(main, '.field-value[data-field-key="Model"]');

        await waitFor(() => span.textContent === "A");
        // Same node, patched in place - not torn down and rebuilt - matches the "never clobber an
        // in-progress edit elsewhere in this card" contract this refresh path exists for.
        expect(mustQuery(main, '.field-value[data-field-key="Model"]')).toBe(span);
    });

    it("shows 'Request failed' and a failed apply-status when the PUT itself fails (network failure)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]'));
        input.value = "10";
        failNextPut(controls, "network");
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/request failed/i);
        // The whole request never got a per-field breakdown at all, so every submitted field's own
        // box shows the same "internal or communication error" purple as the card, not silently
        // nothing (legacy's own PUT catch handler never colored anything - console.error only).
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("failed");
        // The Apply button is re-enabled afterward, not left permanently stuck.
        expect(/** @type {HTMLButtonElement} */ (mustQuery(main, ".apply-button")).disabled).toBe(false);
    });

    it("shows Failed, not silently Valid, when the PUT body is rejected as malformed (HTTP 200, res:ERR)", async () => {
        // make_response(1) for a malformed body is HTTP 200 with res:"ERR" (Part A.8/A.5), never
        // a shaped HTTP error status - so render.js has to check envelope.res itself rather than
        // let an empty `result` fall through to applyResultStyling()'s severity fallback.
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]'));
        input.value = "10";
        failNextPut(controls, "malformed-body");
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/invalid json request/i);
    });

    it("shows Failed with the server's own descr when a PUT hits a shaped HTTP error (500)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]'));
        input.value = "10";
        failNextPut(controls, 500);
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/internal server error/i);
    });

    it("shows Failed when a PUT response body is empty (a torn/truncated transmission)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]'));
        input.value = "10";
        failNextPut(controls, "empty-body");
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        expect(mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus).toBe("failed");
    });

    it("shows Failed for a field missing from a nominally-OK PUT response, without losing the other field's real status (defensive fallback)", async () => {
        // Defensive only: the server answers every submitted key (SPECIFICATION.md A.8).
        uninstall = installMockFetch(DEFS, DATA);
        const mockedFetch = window.fetch;
        window.fetch = (input, init) => {
            if (String(input) === "/sensors" && init?.method === "PUT") {
                const answer = { res: "OK", code: 0, descr: "Command executed", result: { SCD30: { COffset: "Valid" } } };
                return Promise.resolve(new Response(JSON.stringify(answer), { status: 200 }));
            }
            return mockedFetch(input, init);
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]')).value = "10";
        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="COffset"]')).value = "20";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed"); // worst-first: Failed beats whatever the other fields say
        expect(mustQuery(card, ".apply-result").textContent).toContain("MeasInterval: Failed");
        expect(mustQuery(card, ".apply-result").textContent).toContain("COffset: Valid");
        // The reconciled Failed status reaches the field's own box too, not just the card border.
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBe("valid");
    });

    describe("the section controller", () => {
        /** @type {import("../js/definitions.js").Section} */
        const LIVE_STATUS = { ...getSection("status"), pollGroup: "live" };

        it("keeps the same card and readonly value node across three polls", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const requests = recordRequests();
            const main = mount();
            stop = renderSection(DEFS, getSection("measurements"), main);
            await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
            const card = mustQuery(main, '[data-group-key="SCD30"]');
            const value = mustQuery(main, '[data-field-key="CO2"]');

            const seen = requests.length;
            await waitFor(() => requests.length >= seen + 3);
            expect(mustQuery(main, '[data-group-key="SCD30"]')).toBe(card);
            expect(mustQuery(main, '[data-field-key="CO2"]')).toBe(value);
        });

        it("keeps focus on the errcount card's 'Show all' across a poll", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const requests = recordRequests();
            const main = mount();
            stop = renderSection(DEFS, LIVE_STATUS, main);
            await waitFor(() => main.querySelector('[data-errcount-action="all"]') !== null);
            const showAll = mustQuery(main, '[data-errcount-action="all"]');
            showAll.click();
            showAll.focus();

            const seen = requests.length;
            await waitFor(() => requests.length >= seen + 2);
            expect(showAll.isConnected).toBe(true);
            expect(document.activeElement).toBe(showAll);
        });

        it("aborts the GET on the wire when no section follows the stop (the page stops), painting nothing when it settles", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            /** @type {(() => void)[]} */
            const releases = [];
            /** @type {(AbortSignal | null | undefined)[]} */
            const signals = [];
            const inner = window.fetch;
            window.fetch = (input, init) => {
                if (String(input) !== "/measurements") {
                    return inner(input, init);
                }
                signals.push(init?.signal);
                return new Promise((resolve) => {
                    releases.push(() => resolve(new Response(JSON.stringify(DATA.measurements), { status: 200 })));
                });
            };
            const main = mount();
            const stopSection = renderSection(DEFS, getSection("measurements"), main);
            await waitFor(() => releases.length > 0);

            stopSection();
            await waitFor(() => signals[0]?.aborted === true);
            for (const release of releases) {
                release();
            }
            await new Promise((resolve) => {
                setTimeout(resolve, 50);
            });
            expect(main.querySelector("[data-group-key]")).toBeNull();
            expect(mustQuery(main, ".error-banner").dataset.shown).toBe("false");
        });

        it("on a section switch lets the left GET on the wire run to its end, discarded, and queues the next section's first GET behind it", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const consoleError = vi.spyOn(console, "error");
            const observe = vi.fn();
            /** @type {(() => void)[]} */
            const releases = [];
            /** @type {(AbortSignal | null | undefined)[]} */
            const signals = [];
            const inner = window.fetch;
            window.fetch = (input, init) => {
                if (String(input) !== "/status") {
                    return inner(input, init);
                }
                signals.push(init?.signal);
                // A real fetch rejects once its signal aborts; this one never answers otherwise.
                return new Promise((resolve, reject) => {
                    init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
                    releases.push(() => resolve(new Response(JSON.stringify(DATA.status), { status: 200 })));
                });
            };
            const requests = recordRequests();
            const main = mount();
            const stopStatus = renderSection(DEFS, LIVE_STATUS, main, { deviceClock: { nowS: () => null, observe } });
            await waitFor(() => releases.length > 0);
            const leftGrid = mustQuery(main, ".group-grid");
            const leftBanner = mustQuery(main, ".error-banner");

            stopStatus();
            stop = renderSection(DEFS, getSection("sensors"), main);
            await new Promise((resolve) => {
                setTimeout(resolve, 50);
            });
            expect(signals[0]?.aborted).toBe(false);
            expect(requests).toEqual(["GET /status"]);

            for (const release of releases) {
                release();
            }
            await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);
            expect(requests).toEqual(["GET /status", "GET /sensors"]);
            expect(leftGrid.childElementCount).toBe(0);
            expect(leftBanner.dataset.shown).toBe("false");
            expect(observe).not.toHaveBeenCalled();
            expect(mustQuery(main, ".error-banner").dataset.shown).toBe("false");
            expect(consoleError).not.toHaveBeenCalled();
        });

        it("aborts a GET a switch took over once the page stops with no section following", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            /** @type {(AbortSignal | null | undefined)[]} */
            const signals = [];
            const inner = window.fetch;
            window.fetch = (input, init) => {
                if (String(input) !== "/status") {
                    return inner(input, init);
                }
                signals.push(init?.signal);
                // Answers only by rejecting once its signal aborts, as a hung connection would.
                return new Promise((_resolve, reject) => {
                    init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
                });
            };
            const main = mount();
            const stopStatus = renderSection(DEFS, LIVE_STATUS, main);
            await waitFor(() => signals.length > 0);
            stopStatus();
            const stopSensors = renderSection(DEFS, getSection("sensors"), main);
            await new Promise((resolve) => {
                setTimeout(resolve, 50);
            });
            expect(signals[0]?.aborted).toBe(false);

            stopSensors();
            await waitFor(() => signals[0]?.aborted === true);
        });

        it("reads a statusPath field's value from GET /status on a section that reads another route", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                key: "networking",
                label: "Networking",
                rest: { get: "/networking", put: "/networking" },
                pollGroup: "settings",
                groups: [{ key: "link", label: "Link", fields: [{ key: "IP", label: "Address", kind: "readonly", statusPath: ["networking", "IP"] }] }],
            };
            const defs = { ...DEFS, sections: [...DEFS.sections, section] };
            uninstall = installMockFetch(defs, { ...DATA, status: { ...DATA.status, networking: { IP: "10.0.0.7" } } });
            const main = mount();
            stop = renderSection(defs, section, main);

            await waitFor(() => main.querySelector('[data-field-key="IP"]')?.textContent === "10.0.0.7");
        });

        it("shows a degraded /status source as unavailable in every field of its card, with the card's cue", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                key: "status",
                label: "Status",
                rest: { get: "/status" },
                pollGroup: "settings",
                groups: [
                    {
                        key: "system",
                        label: "System Status",
                        fields: [
                            { key: "SysUptime", label: "Uptime", unit: "s", kind: "readonly" },
                            { key: "UTCTime", label: "UTC Time", kind: "readonly", format: "gmtimestruct" },
                        ],
                    },
                    { key: "networking", label: "Network Status", fields: [{ key: "RSSI", label: "Signal", kind: "readonly" }] },
                ],
            };
            const defs = { ...DEFS, sections: [...DEFS.sections.filter((s) => s.key !== "status"), section] };
            uninstall = installMockFetch(defs, DATA);
            answerGets({ "/status": [{ system: { error: "unavailable" }, networking: { RSSI: -60 }, sensors: {}, notification: {}, errcount: {} }] });
            const main = mount();
            stop = renderSection(defs, section, main);

            await waitFor(() => main.querySelector('[data-field-key="RSSI"]')?.textContent === "-60");
            const system = mustQuery(main, '[data-group-key="system"]');
            expect(system.dataset.sourceState).toBe("unavailable");
            const values = [...system.querySelectorAll(".field-value")].map((el) => el.textContent);
            expect(values).toEqual(["unavailable", "unavailable"]);
            expect(mustQuery(main, '[data-group-key="networking"]').dataset.sourceState).toBeUndefined();
        });

        it("updates a sensor card in place to unavailable when a refresh sends its marker, and back when the map returns", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                key: "sensors",
                label: "Sensors",
                rest: { get: "/sensors", put: "/sensors" },
                pollGroup: "live",
                pollIntervalMs: 200,
                groups: [
                    { key: "SCD30", label: "SCD30", submit: true, fields: [{ key: "MeasInterval", label: "Interval", kind: "number" }] },
                    { key: "BMP3XX", label: "BMP3XX", submit: true, fields: [{ key: "SampleInterv", label: "Interval", kind: "number" }] },
                ],
            };
            const defs = { ...DEFS, sections: [...DEFS.sections.filter((s) => s.key !== "sensors"), section] };
            uninstall = installMockFetch(defs, DATA);
            answerGets({
                "/sensors": [
                    { SCD30: { MeasInterval: 5 }, BMP3XX: { SampleInterv: 7 } },
                    { SCD30: { error: "unavailable" }, BMP3XX: { SampleInterv: 7 } },
                    { SCD30: { MeasInterval: 6 }, BMP3XX: { SampleInterv: 7 } },
                ],
            });
            const main = mount();
            stop = renderSection(defs, section, main);
            await waitFor(() => main.querySelector('[data-group-key="SCD30"] [data-current-value-for]')?.textContent?.includes("5") === true);
            const card = mustQuery(main, '[data-group-key="SCD30"]');
            const caption = mustQuery(card, "[data-current-value-for]");

            await waitFor(() => card.dataset.sourceState === "unavailable");
            expect(mustQuery(main, '[data-group-key="SCD30"]')).toBe(card);
            expect(caption.textContent).toContain("unavailable");
            expect(mustQuery(main, '[data-group-key="BMP3XX"]').dataset.sourceState).toBeUndefined();
            expect(mustQuery(main, '[data-group-key="BMP3XX"] [data-current-value-for]').textContent).toContain("7");

            await waitFor(() => caption.textContent?.includes("6") === true);
            expect(card.dataset.sourceState).toBeUndefined();
        });

        it("renders every errcount row as no data when /status carries no errcount", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            answerGets({ "/status": [{ system: {}, networking: {}, sensors: {}, notification: {} }] });
            const main = mount();
            stop = renderSection(DEFS, getSection("status"), main);
            await waitFor(() => main.querySelector('[data-errcount-action="all"]') !== null);

            mustQuery(main, '[data-errcount-action="all"]').click();
            expect(mustQuery(main, ".errcount-row-count").textContent).toBe("no data");
        });

        it("renders an errcount entry sent as the unavailable marker as unavailable", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            answerGets({ "/status": [{ system: {}, networking: {}, sensors: {}, notification: {}, errcount: { SCD30: { error: "unavailable" } } }] });
            const main = mount();
            stop = renderSection(DEFS, getSection("status"), main);
            await waitFor(() => main.querySelector('[data-errcount-action="all"]') !== null);

            mustQuery(main, '[data-errcount-action="all"]').click();
            expect(mustQuery(main, ".errcount-row-count").textContent).toBe("unavailable");
        });

        it("feeds every /status body it reads to the device clock, its own GET's and a sub-request's alike", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const main = mount();
            const observeOwn = vi.fn();
            const stopStatus = renderSection(DEFS, getSection("status"), main, { deviceClock: { nowS: () => null, observe: observeOwn } });
            await waitFor(() => observeOwn.mock.calls.length > 0);
            stopStatus();
            expect(observeOwn.mock.calls[0]?.[0]).toHaveProperty("errcount");

            const observeSub = vi.fn();
            stop = renderSection(DEFS, getSection("notification"), main, { deviceClock: { nowS: () => null, observe: observeSub } });
            await waitFor(() => observeSub.mock.calls.length > 0);
            expect(observeSub.mock.calls.every(([body]) => typeof body === "object" && body !== null && "errcount" in body)).toBe(true);
        });

        it("shows an epoch field as its age against the device clock, and a float without decimals at the site default", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                key: "measurements",
                label: "Measurements",
                rest: { get: "/measurements" },
                pollGroup: "live",
                groups: [
                    {
                        key: "SCD30",
                        label: "SCD30",
                        fields: [
                            { key: "Temp", label: "Temperature", kind: "readonly" },
                            { key: "TS", label: "Measured", kind: "readonly", format: "epoch" },
                        ],
                    },
                ],
            };
            const defs = { ...DEFS, defaultDecimals: 2, sections: [section] };
            uninstall = installMockFetch(defs, DATA);
            answerGets({ "/measurements": [{ SCD30: { Temp: 21.456789, TS: 1000 } }] });
            const main = mount();
            stop = renderSection(defs, section, main, { deviceClock: { nowS: () => 1030, observe: vi.fn() } });

            await waitFor(() => main.querySelector('[data-field-key="TS"]') !== null);
            expect(mustQuery(main, '[data-field-key="TS"]').textContent).toBe("30 s ago");
            expect(mustQuery(main, '[data-field-key="Temp"]').textContent).toBe("21.46");
        });

        it("calls onRecovered once when a failure episode ends, never on a plain success", async () => {
            const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
            uninstall = installMockFetch(DEFS, DATA, controls);
            const onRecovered = vi.fn();
            const main = mount();
            stop = renderSection(DEFS, { ...getSection("measurements"), pollIntervalMs: 200 }, main, { onRecovered });
            await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
            expect(onRecovered).not.toHaveBeenCalled();

            controls.nextFailure = 500;
            const banner = mustQuery(main, ".error-banner");
            await waitFor(() => banner.dataset.shown === "true");
            await waitFor(() => banner.dataset.shown === "false", BANNER_WAIT_MS);
            expect(onRecovered).toHaveBeenCalledTimes(1);
        });

        it("logs console.error once per failure episode, not once per failed tick", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const consoleError = vi.spyOn(console, "error").mockImplementation(() => { /* swallow the logged failure - this test asserts on the spy */ });
            const failures = { left: 0 };
            const inner = window.fetch;
            window.fetch = (input, init) => {
                if (String(input) === "/measurements" && failures.left > 0) {
                    failures.left -= 1;
                    return Promise.resolve(new Response(JSON.stringify({ res: "ERR", code: 500, descr: "Internal server error", result: {} }), { status: 500 }));
                }
                return inner(input, init);
            };
            const main = mount();
            stop = renderSection(DEFS, getSection("measurements"), main);
            await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
            const banner = mustQuery(main, ".error-banner");

            failures.left = 3;
            await waitFor(() => failures.left === 0);
            await waitFor(() => banner.dataset.shown === "false", BANNER_WAIT_MS);
            expect(consoleError).toHaveBeenCalledTimes(1);
            expect(consoleError.mock.calls[0]?.[0]).toBe("Could not refresh Measurements:");

            failures.left = 1;
            await waitFor(() => consoleError.mock.calls.length === 2, BANNER_WAIT_MS);
        });

        it("counts an Apply on the shell's tracker from the click until its post-write GET settles", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const log = recordRequests();
            const applyTracker = {
                begin: () => {
                    log.push("begin");
                },
                end: () => {
                    log.push("end");
                },
            };
            const main = mount();
            stop = renderSection(DEFS, getSection("sensors"), main, { applyTracker });
            await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

            /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]')).value = "10";
            mustQuery(main, ".apply-button").click();
            await waitFor(() => log.includes("end"));
            expect(log.slice(log.indexOf("begin"))).toEqual(["begin", "PUT /sensors", "GET /sensors", "end"]);
        });

        it("shows the banner when a GET answers JSON that is not an object, never a silent dash everywhere", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const inner = window.fetch;
            window.fetch = (input, init) => (String(input) === "/measurements" ? Promise.resolve(new Response("[1, 2]", { status: 200 })) : inner(input, init));
            const main = mount();
            stop = renderSection(DEFS, getSection("measurements"), main);

            await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
            expect(mustQuery(main, ".error-banner").textContent).toMatch(/GET \/measurements returned no JSON object/);
            expect(main.querySelector("[data-group-key]")).toBeNull();
        });

        it("words a failed GET whose body is not JSON by its status, not as an empty body", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const inner = window.fetch;
            window.fetch = (input, init) => (String(input) === "/measurements" ? Promise.resolve(new Response("<p>gone</p>", { status: 404 })) : inner(input, init));
            const main = mount();
            stop = renderSection(DEFS, getSection("measurements"), main);

            await waitFor(() => mustQuery(main, ".error-banner").dataset.shown === "true");
            expect(mustQuery(main, ".error-banner").textContent).toContain("GET /measurements failed: HTTP 404");
        });

        it("refreshes a writable field's caption through its statusPath on every poll", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = { ...getSection("notification"), pollGroup: "live", pollIntervalMs: 50 };
            uninstall = installMockFetch(withSection(section), DATA);
            const statusBody = (/** @type {number} */ pauseTime) => ({ system: {}, networking: {}, sensors: {}, notification: { PauseTime: pauseTime }, errcount: {} });
            answerGets({ "/status": [statusBody(0), statusBody(120)] });
            const main = mount();
            stop = renderSection(withSection(section), section, main);

            await waitFor(() => main.querySelector('[data-current-value-for="PauseTime"]')?.textContent === "Current value: 0");
            const caption = mustQuery(main, '[data-current-value-for="PauseTime"]');
            await waitFor(() => caption.textContent === "Current value: 120");
        });

        it("ends the shell's Apply count after a failed PUT too", async () => {
            const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
            uninstall = installMockFetch(DEFS, DATA, controls);
            failNextPut(controls, "network");
            const applyTracker = { begin: vi.fn(), end: vi.fn() };
            const main = mount();
            stop = renderSection(DEFS, getSection("sensors"), main, { applyTracker });
            await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);

            /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInterval"]')).value = "10";
            const card = mustQuery(main, '[data-group-key="SCD30"]');
            await applyAndSettle(card);
            expect(card.dataset.applyStatus).toBe("failed");
            expect(applyTracker.begin).toHaveBeenCalledTimes(1);
            expect(applyTracker.end).toHaveBeenCalledTimes(1);
        });
    });

    describe("the Apply path", () => {
        /** @returns {Promise<HTMLElement>} the sensors section's SCD30 card, rendered against the mock */
        async function mountSensors() {
            const main = mount();
            stop = renderSection(DEFS, getSection("sensors"), main);
            await waitFor(() => main.querySelector('[data-field-key="MeasInterval"]') !== null);
            return mustQuery(main, '[data-group-key="SCD30"]');
        }

        /**
         * @param {HTMLElement} card
         * @param {string} key
         * @returns {HTMLInputElement}
         */
        function inputOf(card, key) {
            return /** @type {HTMLInputElement} */ (mustQuery(card, `[data-field-key="${CSS.escape(key)}"]`));
        }

        it.each(["  ", "0x10", "1e3", "1,5"])("sends number text %j that is not a plain decimal as typed, which the device answers Invalid", async (text) => {
            uninstall = installMockFetch(DEFS, DATA);
            const puts = capturePutBodies();
            const card = await mountSensors();

            inputOf(card, "COffset").value = text;
            await applyAndSettle(card);
            expect(puts).toEqual([{ SCD30: { COffset: text } }]);
            expect(mustQuery(card, ".apply-result").textContent).toContain("COffset: Invalid");
        });

        it("sends a plain decimal with surrounding spaces as its number", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const puts = capturePutBodies();
            const card = await mountSensors();

            inputOf(card, "COffset").value = " 12 ";
            await applyAndSettle(card);
            expect(puts).toEqual([{ SCD30: { COffset: 12 } }]);
            expect(mustQuery(card, ".apply-result").textContent).toContain("COffset: Valid");
        });

        it("sends a float field's whole number as the JSON number", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                ...getSection("sensors"),
                groups: [{ key: "SCD30", label: "SCD30", submit: true, fields: [{ key: "TempOffset", label: "Temperature Offset", kind: "number", float: true, min: 0, max: 20 }] }],
            };
            uninstall = installMockFetch(withSection(section), { ...DATA, sensorsConfig: { SCD30: { TempOffset: 1.5 } } });
            const inner = window.fetch;
            /** @type {string[]} */
            const rawPuts = [];
            window.fetch = (input, init) => {
                if (init?.method === "PUT") {
                    rawPuts.push(String(init.body));
                }
                return inner(input, init);
            };
            const main = mount();
            stop = renderSection(withSection(section), section, main);
            await waitFor(() => main.querySelector('[data-field-key="TempOffset"]') !== null);

            const card = mustQuery(main, '[data-group-key="SCD30"]');
            inputOf(card, "TempOffset").value = "50";
            await applyAndSettle(card);
            expect(rawPuts).toEqual(['{"SCD30":{"TempOffset":50}}']);
        });

        it("sends a dispatch toggle only when On: left Off, Apply has nothing to submit", async () => {
            const defs = withSection(RESET_SECTION);
            uninstall = installMockFetch(defs, DATA);
            const puts = capturePutBodies();
            const main = mount();
            stop = renderSection(defs, RESET_SECTION, main);
            await waitFor(() => main.querySelector('[data-field-key="ResetErrors"]') !== null);

            await applyAndSettle(mustQuery(main, '[data-group-key="resetErrors"]'));
            expect(mustQuery(main, ".apply-result").textContent).toBe("Nothing to submit - no fields were changed.");
            expect(puts).toEqual([]);
        });

        it("keeps an Invalid field's typed text and clears a Valid sibling's", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const card = await mountSensors();

            inputOf(card, "MeasInterval").value = "3000"; // out of range
            inputOf(card, "COffset").value = "20";
            await applyAndSettle(card);
            expect(mustQuery(card, ".apply-result").textContent).toBe("Command executed — MeasInterval: Invalid, COffset: Valid");
            expect(inputOf(card, "MeasInterval").value).toBe("3000");
            expect(inputOf(card, "COffset").value).toBe("");
        });

        it("clears a field's previous colour when a later Apply's result omits it", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const card = await mountSensors();

            inputOf(card, "MeasInterval").value = "3000";
            inputOf(card, "COffset").value = "20";
            await applyAndSettle(card);
            expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBe("valid");

            inputOf(card, "MeasInterval").value = "10";
            inputOf(card, "COffset").value = "";
            await applyAndSettle(card);
            expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("valid");
            expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBeUndefined();
        });

        it("marks the card failed for an unknown result word and shows the word as sent", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            answerPuts("/sensors", { SCD30: { MeasInterval: "Weird" } });
            const card = await mountSensors();

            inputOf(card, "MeasInterval").value = "10";
            await applyAndSettle(card);
            expect(card.dataset.applyStatus).toBe("failed");
            expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("failed");
            expect(mustQuery(card, ".apply-result").textContent).toBe("Command executed — MeasInterval: Weird");
        });

        it("gives every submitted field the one word a sensor answers in place of its field map", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            answerPuts("/sensors", { SCD30: "Invalid" });
            const card = await mountSensors();

            inputOf(card, "MeasInterval").value = "10";
            inputOf(card, "COffset").value = "20";
            await applyAndSettle(card);
            expect(card.dataset.applyStatus).toBe("invalid");
            expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("invalid");
            expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBe("invalid");
            expect(mustQuery(card, ".apply-result").textContent).toBe("Command executed — MeasInterval: Invalid, COffset: Invalid");
        });

        it("shows a toggle and a dropdown as the post-write GET reports them, not as sent", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            // The device reports its own stored values whatever this page sends.
            answerGets({ "/sensors": [{ SCD30: { MeasInterval: 5, COffset: 10, MeasEnabled: true, Oversampling: 1 } }] });
            const puts = capturePutBodies();
            const card = await mountSensors();

            mustQuery(card, '[data-field-key="MeasEnabled"]').click(); // On -> Off
            /** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="Oversampling"]')).value = "4";
            await applyAndSettle(card);
            expect(puts).toEqual([{ SCD30: { MeasEnabled: false, Oversampling: 4 } }]);
            expect(mustQuery(card, '[data-field-key="MeasEnabled"]').dataset.value).toBe("true");
            expect(/** @type {HTMLSelectElement} */ (mustQuery(card, '[data-field-key="Oversampling"]')).value).toBe("1");
        });

        it("keeps the Apply button disabled until the post-write GET settles", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const gate = { putSeen: false, release: () => { /* replaced when the post-write GET arrives */ }, held: false };
            const inner = window.fetch;
            window.fetch = (input, init) => {
                if (init?.method === "PUT") {
                    gate.putSeen = true;
                } else if (gate.putSeen && String(input) === "/sensors") {
                    gate.held = true;
                    return new Promise((resolve) => {
                        gate.release = () => resolve(inner(input, init));
                    });
                }
                return inner(input, init);
            };
            const card = await mountSensors();
            const button = /** @type {HTMLButtonElement} */ (mustQuery(card, ".apply-button"));

            inputOf(card, "MeasInterval").value = "10";
            button.click();
            await waitFor(() => gate.held);
            expect(card.dataset.applyStatus).toBe("valid");
            expect(button.disabled).toBe(true);
            gate.release();
            await waitFor(() => !button.disabled);
        });

        it("keeps a Valid result when the post-write GET fails: the banner shows, Apply re-enables, nothing rejects unhandled", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const unhandled = vi.fn();
            window.addEventListener("unhandledrejection", unhandled);
            try {
                let putSeen = false;
                const inner = window.fetch;
                window.fetch = (input, init) => {
                    if (init?.method === "PUT") {
                        putSeen = true;
                    } else if (putSeen && String(input) === "/sensors") {
                        return Promise.resolve(new Response(JSON.stringify({ res: "ERR", code: 500, descr: "Internal server error", result: {} }), { status: 500 }));
                    }
                    return inner(input, init);
                };
                const card = await mountSensors();

                inputOf(card, "MeasInterval").value = "10";
                await applyAndSettle(card);
                expect(mustQuery(card, '[data-field-wrapper-key="MeasInterval"]').dataset.applyStatus).toBe("valid");
                expect(mustQuery(mainEl ?? document.body, ".error-banner").dataset.shown).toBe("true");
                await new Promise((resolve) => {
                    setTimeout(resolve, 50);
                });
                expect(unhandled).not.toHaveBeenCalled();
            } finally {
                window.removeEventListener("unhandledrejection", unhandled);
            }
        });

        it.each([["erasefram", "Erase FRAM"], ["resetconfig", "Reset to defaults"]])(
            "asks before system command %s, sends exactly it, and returns the select to its placeholder",
            async (value, label) => {
                const defs = withSection(SYSTEM_SECTION);
                uninstall = installMockFetch(defs, DATA);
                const puts = capturePutBodies();
                const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
                const main = mount();
                stop = renderSection(defs, SYSTEM_SECTION, main);
                await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);

                const select = /** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="SystemCmd"]'));
                select.value = value;
                const card = mustQuery(main, '[data-group-key="command"]');
                await applyAndSettle(card);
                expect(confirm.mock.calls).toEqual([[`${label}?`]]);
                expect(puts).toEqual([{ SystemCmd: value }]);
                expect(mustQuery(card, ".apply-result").textContent).toContain("SystemCmd: Valid");
                expect(select.value).toBe("");
                expect(select.selectedOptions[0]?.textContent).toBe("Select…");
            },
        );

        it("sends no system command when its confirmation is declined, and re-enables Apply", async () => {
            const defs = withSection(SYSTEM_SECTION);
            uninstall = installMockFetch(defs, DATA);
            const puts = capturePutBodies();
            vi.spyOn(window, "confirm").mockReturnValue(false);
            const main = mount();
            stop = renderSection(defs, SYSTEM_SECTION, main);
            await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);

            /** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="SystemCmd"]')).value = "reboot";
            const card = mustQuery(main, '[data-group-key="command"]');
            await applyAndSettle(card);
            expect(puts).toEqual([]);
            expect(card.dataset.applyStatus).toBeUndefined();
            // A browser that suppresses dialogs answers false at once: the visitor still sees why nothing happened.
            expect(mustQuery(card, ".apply-result").textContent).toBe("Not sent - the confirmation was declined.");
            expect(/** @type {HTMLButtonElement} */ (mustQuery(card, ".apply-button")).disabled).toBe(false);
            expect(/** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="SystemCmd"]')).value).toBe("reboot");
        });

        it("shows Failed on the field and the card when a system command answers Failed", async () => {
            const defs = withSection(SYSTEM_SECTION);
            uninstall = installMockFetch(defs, DATA);
            answerPuts("/system", { SystemCmd: "Failed" });
            vi.spyOn(window, "confirm").mockReturnValue(true);
            const main = mount();
            stop = renderSection(defs, SYSTEM_SECTION, main);
            await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);

            /** @type {HTMLSelectElement} */ (mustQuery(main, '[data-field-key="SystemCmd"]')).value = "reboot";
            const card = mustQuery(main, '[data-group-key="command"]');
            await applyAndSettle(card);
            expect(card.dataset.applyStatus).toBe("failed");
            expect(mustQuery(card, '[data-field-wrapper-key="SystemCmd"]').dataset.applyStatus).toBe("failed");
        });

        /** @type {import("../js/definitions.js").Section} */
        const DNS_SECTION = {
            key: "networking",
            label: "Networking",
            rest: { get: "/networking", put: "/networking" },
            pollGroup: "settings",
            groups: [{ key: "dns", label: "DNS", submit: true, fields: [{ key: "DNSFallback", label: "DNS Fallback", kind: "string", shape: "ipv4List", clearable: true }] }],
        };
        const DNS_DATA = { ...DATA, networkingConfig: { DNSFallback: "1.1.1.1" } };

        it("DNS fallback Clear: sends exactly an empty list after its confirmation, with no GET before it", async () => {
            uninstall = installMockFetch(withSection(DNS_SECTION), DNS_DATA);
            const log = recordRequests();
            const puts = capturePutBodies();
            const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
            const main = mount();
            stop = renderSection(withSection(DNS_SECTION), DNS_SECTION, main);
            await waitFor(() => main.querySelector("[data-clear-for]") !== null);

            const seen = log.length;
            mustQuery(main, "[data-clear-for]").click();
            await waitFor(() => mustQuery(main, '[data-field-wrapper-key="DNSFallback"]').dataset.applyStatus !== undefined);
            expect(confirm.mock.calls).toEqual([["Clear DNS Fallback?"]]);
            expect(puts).toEqual([{ DNSFallback: "" }]);
            expect(log[seen]).toBe("PUT /networking");
            expect(mustQuery(main, ".apply-result").textContent).toBe("Command executed — DNSFallback: Valid");
        });

        it("DNS fallback Clear: sends nothing on cancel, and an Apply with the input blank never sends the key", async () => {
            uninstall = installMockFetch(withSection(DNS_SECTION), DNS_DATA);
            const puts = capturePutBodies();
            vi.spyOn(window, "confirm").mockReturnValue(false);
            const main = mount();
            stop = renderSection(withSection(DNS_SECTION), DNS_SECTION, main);
            await waitFor(() => main.querySelector("[data-clear-for]") !== null);

            mustQuery(main, "[data-clear-for]").click();
            expect(mustQuery(main, ".apply-result").textContent).toBe("Not sent - the confirmation was declined.");
            await applyAndSettle(mustQuery(main, '[data-group-key="dns"]'));
            expect(puts).toEqual([]);
            expect(mustQuery(main, ".apply-result").textContent).toBe("Nothing to submit - no fields were changed.");
        });

        /** @type {import("../js/definitions.js").Section} */
        const ALTITUDE_SECTION = {
            ...getSection("sensors"),
            groups: [
                {
                    key: "SCD30",
                    label: "SCD30",
                    submit: true,
                    fields: [
                        { key: "AmbPres", label: "Ambient Pressure", unit: "hPa", kind: "number", alwaysExecuted: true },
                        { key: "Altitude", label: "Altitude", unit: "m", kind: "number", ignoredWhenSet: "AmbPres" },
                    ],
                },
            ],
        };

        it.each([
            ["shown while the pressure baseline is non-zero", 1013, "", ["100"], "true"],
            ["hidden while the pressure baseline is zero", 0, "", ["100"], "false"],
            ["hidden once the Altitude input is cleared", 1013, "", ["100", ""], "false"],
            ["hidden when 0 is typed as the pressure", 1013, "0", ["100"], "false"],
            ["shown when a pressure is typed over a zero baseline", 0, "1000", ["100"], "true"],
        ])("the Altitude warning is %s", async (_title, baseline, pressureTyped, altitudeSteps, shown) => {
            uninstall = installMockFetch(withSection(ALTITUDE_SECTION), { ...DATA, sensorsConfig: { SCD30: { AmbPres: baseline, Altitude: 0 } } });
            const main = mount();
            stop = renderSection(withSection(ALTITUDE_SECTION), ALTITUDE_SECTION, main);
            await waitFor(() => main.querySelector('[data-field-key="Altitude"]') !== null);

            const card = mustQuery(main, '[data-group-key="SCD30"]');
            typeInto(inputOf(card, "AmbPres"), pressureTyped);
            for (const step of altitudeSteps) {
                typeInto(inputOf(card, "Altitude"), step);
            }
            expect(mustQuery(card, ".field-warning").dataset.shown).toBe(shown);
        });

        it("never sends a password mask: the inputs start empty under the dots, and only a typed password is sent", async () => {
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                key: "networking",
                label: "Networking",
                rest: { get: "/networking", put: "/networking" },
                pollGroup: "settings",
                groups: [
                    {
                        key: "identity",
                        label: "Wi-Fi & Identity",
                        submit: true,
                        fields: [
                            { key: "SSID", label: "Wi-Fi SSID", kind: "string" },
                            { key: "PW", label: "Wi-Fi Password", kind: "string", mask: true },
                            { key: "HotspotPW", label: "Hotspot Password", kind: "string", mask: true },
                        ],
                    },
                ],
            };
            uninstall = installMockFetch(withSection(section), { ...DATA, networkingConfig: { SSID: "home", PW: "secret1", HotspotPW: "hotspot1" } });
            const puts = capturePutBodies();
            const main = mount();
            stop = renderSection(withSection(section), section, main);
            await waitFor(() => main.querySelector('[data-field-key="PW"]') !== null);

            const card = mustQuery(main, '[data-group-key="identity"]');
            for (const key of ["PW", "HotspotPW"]) {
                expect(inputOf(card, key).value).toBe("");
                expect(inputOf(card, key).placeholder).toBe("••••••••");
                expect(mustQuery(card, `[data-current-value-for="${key}"]`).textContent).toBe("Current value: ••••••••");
            }
            inputOf(card, "SSID").value = "newnet";
            await applyAndSettle(card);
            inputOf(card, "PW").value = "pass word1";
            await applyAndSettle(card);
            inputOf(card, "HotspotPW").value = "hot spot2";
            await applyAndSettle(card);
            expect(puts).toEqual([{ SSID: "newnet" }, { PW: "pass word1" }, { HotspotPW: "hot spot2" }]);
        });

        it("renders, collects, sends and colours keys that are hostile in a selector", async () => {
            const groupKey = 'g"]';
            const keys = ['a"] [x="', "b\\c", "d e"];
            /** @type {import("../js/definitions.js").Section} */
            const section = {
                ...getSection("sensors"),
                groups: [{ key: groupKey, label: "Hostile", submit: true, fields: keys.map((key) => ({ key, label: key, kind: /** @type {const} */ ("number"), min: 0, max: 100 })) }],
            };
            uninstall = installMockFetch(withSection(section), { ...DATA, sensorsConfig: { [groupKey]: Object.fromEntries(keys.map((key) => [key, 1])) } });
            const puts = capturePutBodies();
            const main = mount();
            stop = renderSection(withSection(section), section, main);
            await waitFor(() => main.querySelectorAll("[data-field-wrapper-key]").length === keys.length);

            const card = mustQuery(main, `[data-group-key="${CSS.escape(groupKey)}"]`);
            for (const key of keys) {
                inputOf(card, key).value = "5";
            }
            await applyAndSettle(card);
            expect(puts).toEqual([{ [groupKey]: Object.fromEntries(keys.map((key) => [key, 5])) }]);
            for (const key of keys) {
                expect(mustQuery(card, `[data-field-wrapper-key="${CSS.escape(key)}"]`).dataset.applyStatus).toBe("valid");
            }
        });

        /**
         * Another client stores `values` on the device behind this page's back.
         * @param {Record<string, unknown>} values
         */
        async function anotherClientWrites(values) {
            const response = await window.fetch("/sensors", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ SCD30: values }) });
            expect(response.ok).toBe(true);
            expect((await response.json()).code).toBe(0); // HTTP 200 alone also carries a refused body's code 1
        }

        it("sends one GET of the section before the PUT, and a toggle and dropdown another client changed", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const card = await mountSensors();
            await anotherClientWrites({ MeasEnabled: false, Oversampling: 4 });
            const button = /** @type {HTMLButtonElement} */ (mustQuery(card, ".apply-button"));
            /** @type {string[]} */
            const log = [];
            const inner = window.fetch;
            window.fetch = (input, init) => {
                log.push(`${init?.method ?? "GET"} ${String(input)} disabled=${String(button.disabled)}`);
                return inner(input, init);
            };
            const puts = capturePutBodies();

            // The page still shows On and x1; the visitor wants exactly those.
            await applyAndSettle(card);
            expect(log).toEqual(["GET /sensors disabled=true", "PUT /sensors disabled=true", "GET /sensors disabled=true"]);
            expect(puts).toEqual([{ SCD30: { MeasEnabled: true, Oversampling: 1 } }]);
        });

        it("has nothing to submit when the form equals the refreshed values, and re-enables Apply", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const card = await mountSensors();
            await anotherClientWrites({ MeasEnabled: false });
            const puts = capturePutBodies();

            mustQuery(card, '[data-field-key="MeasEnabled"]').click(); // On -> Off, what the device now holds
            await applyAndSettle(card);
            expect(puts).toEqual([]);
            expect(mustQuery(card, ".apply-result").textContent).toBe("Nothing to submit - no fields were changed.");
            expect(/** @type {HTMLButtonElement} */ (mustQuery(card, ".apply-button")).disabled).toBe(false);
        });

        it("sends no GET from a stopped section", async () => {
            uninstall = installMockFetch(DEFS, DATA);
            const card = await mountSensors();
            const log = recordRequests();
            stop?.();
            stop = undefined;

            inputOf(card, "MeasInterval").value = "10";
            await applyAndSettle(card);
            expect(log.filter((entry) => entry.startsWith("GET"))).toEqual([]);
        });
    });
});
