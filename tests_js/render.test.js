import { afterEach, describe, expect, it, vi } from "vitest";
import { installMockFetch } from "../js/mock-server.js";
import { renderSection } from "../js/render.js";

// Polls `check` instead of a fixed sleep - the mock server's fetch has randomized latency
// (js/mock-server.js) and some flows chain two calls, so a fixed wait would be flaky or slow.
/**
 * @param {() => unknown} check
 * @param {number} [timeoutMs]
 */
async function waitFor(check, timeoutMs = 2000) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (check()) {
            return;
        }
        // Intentionally sequential: each retry must wait out the previous delay before rechecking.
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => {
            setTimeout(resolve, 10);
        });
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
                        // min: 0 deliberately, to catch a form input coerced to the number 0 by
                        // accident (e.g. non-numeric text) rather than one genuinely submitted as 0.
                        { key: "COffset", label: "Calibration Offset", kind: "number", min: 0, max: 500 },
                        // Named unlike the real SCD30 field "ContMeas" on purpose - js/mock-server.js
                        // now special-cases that exact key name for a real hardware quirk
                        // (SPECIFICATION.md Part H.7), which this fixture's own generic toggle-rendering
                        // scenario must stay clear of.
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
    sensorsConfig: { SCD30: { MeasInt: 5, COffset: 10, MeasEnabled: true, Oversampling: 1 } },
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

        const toggle = mustQuery(main, '[data-field-key="MeasEnabled"]');
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
        // The field's own box carries its own result too, not just the card-level worst status
        // (legacy per-field granularity, restored alongside the new accent-stripe presentation).
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInt"]').dataset.applyStatus).toBe("invalid");
    });

    it("colors each individual field's own box by its own result, not just the card's worst status", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]')).value = "3000"; // out of range
        // COffset and MeasEnabled are left untouched on purpose - a number field's sparse-PUT
        // convention omits a blank input, and a non-dispatch toggle/enum field (unlike the real
        // ContMeas/SystemCmd/ResetErrors/SGPResetVOC) is now sparse-omitted the same way when it
        // still matches its current value (collectGroupBody()).
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid"); // worst-first across the whole group

        expect(mustQuery(card, '[data-field-wrapper-key="MeasInt"]').dataset.applyStatus).toBe("invalid");
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
        // and are never touched - only MeasInt is genuinely changed.
        /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]')).value = "10";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("valid");
        // Only the field that actually changed shows up in the result text.
        expect(mustQuery(card, ".apply-result").textContent).toBe("OK — MeasInt: Valid");
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

    it("preserves an expanded errcount card's 'Show flagged'/'Show all' state across a live poll rebuild", async () => {
        // Both real definitions files (wozi.json/dev.json) declare "status" as pollGroup "live" -
        // this fixture's own DEFS deliberately doesn't (see its own comment), so this scenario
        // needs its own local variant to actually exercise the poll-rebuild path, same pattern as
        // the "readonly field embedded in a writable, live-polled group" test above.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithLiveErrcount = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "status"),
                { ...getSection("status"), pollGroup: "live", pollIntervalMs: 1000 },
            ],
        };
        uninstall = installMockFetch(defsWithLiveErrcount, DATA);
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithLiveErrcount.sections.find((s) => s.key === "status"));
        stop = renderSection(defsWithLiveErrcount, section, main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        mustQuery(main, '[data-errcount-action="flagged"]').click();
        expect(mustQuery(main, ".errcount-module-list").classList.contains("hidden")).toBe(false);

        // Fake timers only from here on - js/mock-server.js's own fetch adds up to ~200ms of
        // randomized latency via a real setTimeout, which the waitFor() above (real timers) needs
        // to observe directly; switching earlier would hang waitFor's own real-timer polling loop.
        vi.useFakeTimers();
        await vi.advanceTimersByTimeAsync(1200); // one live-poll tick (1000ms) + its own fetch latency

        // Before the fix, the poll rebuild unconditionally reset to the default collapsed state -
        // a visitor mid-read of the flagged rows would see them vanish underneath them.
        expect(mustQuery(main, ".errcount-module-list").classList.contains("hidden")).toBe(false);
        expect(mustQuery(main, ".errcount-row").textContent).toContain("2");

        vi.useRealTimers();
    });

    it("shows Valid (not Failed) after a successful Reset All Errors submission, even though /status's PUT never returns a per-field result", async () => {
        // src/asy_webserver_service.py's _put_status() never builds a `result` dict at all
        // (ar.make_response(0), no result kwarg) - unlike every other writable endpoint, /status's
        // PUT structurally can't report a per-field outcome. reconcileResults()'s "submitted but
        // missing from the response = Failed" heuristic exists to catch a different, real
        // server-side gap (a settings group's post-write hook dropping fields) and must not apply
        // here, or a successful reset would always render as Failed (regression coverage).
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithResetErrors = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "status"),
                {
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
                            fields: [{ key: "ResetErrors", label: "Confirm Reset", kind: "toggle", onLabel: "Yes, reset", offLabel: "No", dispatch: true }],
                        },
                    ],
                },
            ],
        };
        uninstall = installMockFetch(defsWithResetErrors, DATA);
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithResetErrors.sections.find((s) => s.key === "status"));
        stop = renderSection(defsWithResetErrors, section, main);
        await waitFor(() => main.querySelector('[data-field-key="ResetErrors"]') !== null);

        mustQuery(main, '[data-field-key="ResetErrors"]').click(); // flips the toggle to "Yes, reset"
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="resetErrors"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="resetErrors"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, '[data-field-wrapper-key="ResetErrors"]').dataset.applyStatus).toBe("valid");

        // ResetErrors is a dispatched action, re-run fresh every call - a second, identical
        // submission (the toggle stays "Yes, reset") must still report Valid, never Unchanged,
        // matching every other dispatch-only field's own "always triggers" guarantee
        // (SystemCmd/PauseTime/lightCmdLED - already covered by their own dedicated tests).
        const button = /** @type {HTMLButtonElement} */ (mustQuery(main, ".apply-button"));
        button.click();
        await waitFor(() => button.disabled); // request in flight
        await waitFor(() => !button.disabled); // request settled
        expect(card.dataset.applyStatus).toBe("valid");
    });

    it("skips the PUT and shows a neutral message when Apply is clicked with nothing to submit", async () => {
        // A group made only of number/string fields (unlike a toggle, or an enum with a real
        // current value, both of which always resubmit) can be genuinely empty if the visitor
        // clicks Apply without touching anything - collectGroupBody() then returns {}. Sending that
        // as a real PUT would round-trip
        // to the server for nothing and, since applyResultStyling()'s empty-result fallback is
        // "Valid", would misleadingly show green success for a request that changed nothing.
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
        // No PUT was actually sent, so no outcome to color - the card must not claim a status
        // (particularly not the misleading "valid" an empty-result PUT response would produce).
        expect(card.dataset.applyStatus).toBeUndefined();
    });

    it("skips the PUT for an enum-only submit group (e.g. SystemCmd) left untouched, instead of silently dispatching whichever command the browser defaults a bare <select> to (regression)", async () => {
        // SystemCmd is never returned by GET /system (write-only dispatched action -
        // SPECIFICATION.md Part A.8), so buildField() has no real current value to preselect. Before
        // the templates.js fix, a native <select> with no option explicitly marked selected defaults
        // to its first <option> - so visiting the System section and clicking Apply without ever
        // touching the dropdown silently PUT {"SystemCmd":"reboot"}, confirmed live in Chromium.
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsSystemCmd = {
            ...DEFS,
            sections: [
                ...DEFS.sections.filter((s) => s.key !== "system"),
                {
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
                                    options: [
                                        { value: "reboot", label: "Reboot" },
                                        { value: "bootloader", label: "Reboot into bootloader" },
                                        { value: "mempause", label: "Pause backups for 5 minutes" },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        };
        uninstall = installMockFetch(defsSystemCmd, DATA);
        // Layered on top of the mock's own fetch - afterEach's uninstall() call restores the true
        // original regardless of how many times window.fetch was reassigned in between, so no
        // manual restore is needed here.
        const mockedFetch = window.fetch;
        let putSent = false;
        window.fetch = async (input, init) => {
            if (String(input) === "/system" && init?.method === "PUT") {
                putSent = true;
            }
            return mockedFetch(input, init);
        };

        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsSystemCmd.sections.find((s) => s.key === "system"));
        stop = renderSection(defsSystemCmd, section, main);
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
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => main.querySelector('[data-field-key="CO2"]') !== null);
        const banner = mustQuery(main, ".error-banner");
        expect(banner.classList.contains("hidden")).toBe(true);

        controls.nextFailure = 500;
        await waitFor(() => !banner.classList.contains("hidden"));
        expect(banner.textContent).toMatch(/measurements/i);
        // The server's own shaped-error descr surfaces verbatim, not just a bare status code.
        expect(banner.textContent).toMatch(/simulated failure/i);
        // Stale data from before the failure is still on screen, not wiped out.
        expect(main.querySelector('[data-field-key="CO2"]')).not.toBeNull();

        await waitFor(() => banner.classList.contains("hidden"), 5000);
    });

    it("shows a visible error banner when a settings section's one-shot GET fails", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("network") };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/sensors/i);
    });

    it("reports Invalid for non-numeric text in a number field instead of silently submitting 0 (regression)", async () => {
        // JSON.stringify(NaN) is "null", so a naive Number("abc") -> NaN -> PUT body used to
        // arrive server-side as null, and a naive Number(null) === 0 there made typed garbage
        // look like a deliberate, in-range "0" instead of failing validation. COffset's min is 0
        // specifically so this can't pass by accident the way a min>0 field's own out-of-range
        // rejection would.
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

    it("reports Failed (not Invalid) for non-numeric text in a composite subfield instead of silently submitting 0 (regression)", async () => {
        // Same NaN -> null -> 0 gap as the top-level number-field case above, but through
        // collectGroupBody()'s separate composite-field code path - r's min is 0, so a garbage
        // "r" that silently became 0 would otherwise pass. "Failed", not "Invalid": the real
        // backend never range/type-checks lightCmdLED at the dispatch layer (only
        // isinstance(payload, dict)) - a non-numeric subfield only fails inside
        // _notification_led_callback()'s own int()/float() cast, which asy_webserver_service.py's
        // _dispatch_notification_led() catches and reports as "Failed", the same as any other
        // caller-supplied-callback exception.
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="lightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="lightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="r"]')).value = "abc";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="g"]')).value = "50";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="b"]')).value = "50";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="t"]')).value = "1";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toContain("lightCmdLED: Failed");
    });

    it("reports Failed (not Invalid) for a composite field submitted with only some subfields filled", async () => {
        // collectGroupBody() only sends subfields the visitor actually filled in (render.js).
        // lightCmdLED is a dispatch-only action (SPECIFICATION.md Part A.8), not a persisted
        // SettingsGroup field: the real _notification_led_callback() indexes payload["r"]/["g"]/
        // ["b"]/["t"] directly, so a missing subfield raises KeyError inside the callback -
        // _dispatch_notification_led() catches that the same as any other callback exception and
        // reports "Failed", never "Invalid" (which is reserved for a payload that isn't even a
        // dict at all).
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
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toContain("lightCmdLED: Failed");
    });

    it("reports Valid for a fully-specified composite lightCmdLED submission and never persists it (dispatch-only, matches real GET /notification)", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="lightCmdLED"]') !== null);

        const grid = mustQuery(main, '[data-field-key="lightCmdLED"]');
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="r"]')).value = "10";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="g"]')).value = "20";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="b"]')).value = "30";
        /** @type {HTMLInputElement} */ (mustQuery(grid, '[data-sub-field-key="t"]')).value = "1";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="flash"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("lightCmdLED: Valid");
    });

    it("skips the PUT and shows a neutral message when lightCmdLED's Apply is clicked with every subfield left blank", async () => {
        // The "flash" group's only field is the composite lightCmdLED - collectGroupBody()'s
        // composite branch omits it entirely when anyFilled stays false (no subfield touched), the
        // same sparse-PUT "untouched means omit" convention every other field kind already follows -
        // so this is the composite-field instance of the same "nothing to submit" path already
        // covered for a plain string field (SSID) and an enum with no matching current value
        // (SystemCmd).
        uninstall = installMockFetch(DEFS, DATA);
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);
        await waitFor(() => main.querySelector('[data-field-key="lightCmdLED"]') !== null);

        const card = mustQuery(main, '[data-group-key="flash"]');
        mustQuery(card, ".apply-button").click();

        await waitFor(() => mustQuery(card, ".apply-result").textContent !== "");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/nothing to submit/i);
        expect(card.dataset.applyStatus).toBeUndefined();
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

    it("shows a visible error banner when a GET response body is empty", async () => {
        const originalFetch = window.fetch;
        window.fetch = async (input) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/measurements") {
                return new Response("", { status: 200 });
            }
            return originalFetch(input);
        };
        uninstall = () => {
            window.fetch = originalFetch;
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/measurements/i);
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/empty body/i);
    });

    it("shows a clear, non-crashing error banner when a GET response body is torn/truncated JSON (a transmission error)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ ("torn-json") };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("measurements"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/measurements/i);
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/not valid json|corrupted|truncated/i);
    });

    it("surfaces the server's own descr text when the notification section's /status sub-fetch returns a shaped HTTP error", async () => {
        uninstall = installMockFetch(DEFS, DATA);
        const mockedFetch = window.fetch;
        window.fetch = async (input, init) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/status") {
                return new Response(JSON.stringify({ res: "ERR", code: 4, descr: "Not found", result: {} }), { status: 404 });
            }
            return mockedFetch(input, init);
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/not found/i);
    });

    it("shows a visible error banner when the notification section's own /status sub-fetch fails", async () => {
        // The "Pause Notifications" group's current PauseTime value comes from a second, internal
        // GET /status call (render.js's fetchOnce()), separate from the section's own GET
        // /notification - a failure in that second call must surface too, not be swallowed.
        uninstall = installMockFetch(DEFS, DATA);
        const mockedFetch = window.fetch;
        window.fetch = async (input, init) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/status") {
                throw new TypeError("Failed to fetch (simulated)");
            }
            return mockedFetch(input, init);
        };
        const main = mount();
        stop = renderSection(DEFS, getSection("notification"), main);

        await waitFor(() => !mustQuery(main, ".error-banner").classList.contains("hidden"));
        expect(mustQuery(main, ".error-banner").textContent).toMatch(/notification/i);
    });

    it("refreshes a readonly field embedded in a writable, live-polled group in place on the next poll", async () => {
        // Today's real definitions files never nest a readonly field inside a submit:true group
        // within a "live" section, but render.js's own renderer is schema-agnostic and must handle
        // it correctly if a future schema does - this fixture exercises that path directly.
        // Fake timers make the two poll ticks deterministic instead of racing a real interval.
        vi.useFakeTimers();
        /** @type {import("../js/definitions.js").SiteDefinitions} */
        const defsWithReadonlyInWritable = {
            ...DEFS,
            sections: [
                {
                    key: "measurements",
                    label: "Measurements",
                    rest: { get: "/measurements" },
                    pollGroup: "live",
                    pollIntervalMs: 1000,
                    groups: [{ key: "SCD30", label: "SCD30", submit: true, fields: [{ key: "Model", label: "Model", kind: "readonly" }] }],
                },
                ...DEFS.sections.filter((s) => s.key !== "measurements"),
            ],
        };
        let callCount = 0;
        const originalFetch = window.fetch;
        window.fetch = async (input) => {
            const url = typeof input === "string" ? input : input.toString();
            if (url === "/measurements") {
                callCount += 1;
                return new Response(JSON.stringify({ SCD30: { Model: callCount === 1 ? "B" : "A" } }), { status: 200 });
            }
            return originalFetch(input);
        };
        uninstall = () => {
            window.fetch = originalFetch;
        };
        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsWithReadonlyInWritable.sections.find((s) => s.key === "measurements"));
        stop = renderSection(defsWithReadonlyInWritable, section, main);

        await vi.advanceTimersByTimeAsync(0);
        const span = mustQuery(main, '.field-value[data-field-key="Model"]');
        expect(span.textContent).toBe("B");

        await vi.advanceTimersByTimeAsync(1000);
        // Same node, patched in place - not torn down and rebuilt - matches the "never clobber an
        // in-progress edit elsewhere in this card" contract this refresh path exists for.
        expect(mustQuery(main, '.field-value[data-field-key="Model"]')).toBe(span);
        expect(span.textContent).toBe("A");

        vi.useRealTimers();
    });

    it("shows 'Request failed' and a failed apply-status when the PUT itself fails (network failure)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
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
        // The whole request never got a per-field breakdown at all, so every submitted field's own
        // box shows the same "internal or communication error" purple as the card, not silently
        // nothing (legacy's own PUT catch handler never colored anything - console.error only).
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInt"]').dataset.applyStatus).toBe("failed");
        // The Apply button is re-enabled afterward, not left permanently stuck.
        expect(/** @type {HTMLButtonElement} */ (mustQuery(main, ".apply-button")).disabled).toBe(false);
    });

    it("shows Failed, not silently Valid, when the PUT body is rejected as malformed (HTTP 200, res:ERR)", async () => {
        // The real backend's own make_response(1) for a malformed body is HTTP 200 with res:"ERR"
        // (SPECIFICATION.md Part A.8/A.5) - never a shaped HTTP error status, so render.js must
        // check envelope.res itself rather than relying on an empty `result` to fall through to
        // applyResultStyling()'s own severity fallback.
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "10";
        controls.nextFailure = "malformed-body";
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
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "10";
        controls.nextFailure = 500;
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed");
        expect(mustQuery(card, ".apply-result").textContent).toMatch(/simulated failure/i);
    });

    it("shows Failed when a PUT response body is empty (a torn/truncated transmission)", async () => {
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "10";
        controls.nextFailure = "empty-body";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        expect(mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus).toBe("failed");
    });

    it("shows Failed for a field silently missing from a nominally-OK PUT response, without losing the other field's real status", async () => {
        // Real server-side gap (SPECIFICATION.md Part H.6, "Server-side settings-group failure"): a settings group's
        // post-write hook raising drops that group's fields from `result` entirely, while the
        // overall envelope still reports res:"OK". reconcileResults() treats a submitted-but-
        // unanswered field as Failed rather than letting it silently vanish from the UI.
        const controls = { nextFailure: /** @type {import("../js/mock-server.js").MockFailure | undefined} */ (undefined) };
        uninstall = installMockFetch(DEFS, DATA, controls);
        const main = mount();
        stop = renderSection(DEFS, getSection("sensors"), main);
        await waitFor(() => main.querySelector('[data-field-key="MeasInt"]') !== null);

        const input = /** @type {HTMLInputElement} */ (mustQuery(main, '[data-field-key="MeasInt"]'));
        input.value = "10"; // in range - would normally read back Valid
        controls.nextFailure = "partial-result";
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("failed"); // worst-first: Failed beats whatever the other fields say
        expect(mustQuery(card, ".apply-result").textContent).toContain("MeasInt: Failed");
        // The reconciled Failed status reaches the field's own box too, not just the card border.
        expect(mustQuery(card, '[data-field-wrapper-key="MeasInt"]').dataset.applyStatus).toBe("failed");
    });
});
