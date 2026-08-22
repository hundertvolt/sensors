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
    sensorsConfig: { SCD30: { MeasInt: 5, COffset: 10, ContMeas: true, Oversampling: 1 } },
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
        // COffset is left blank on purpose - a number field's sparse-PUT convention omits it
        // entirely (unlike the toggle/enum fields below, which always resubmit their current
        // value and so are never sparse-omittable through this UI).
        mustQuery(main, ".apply-button").click();

        await waitFor(() => mustQuery(main, '[data-group-key="SCD30"]').dataset.applyStatus !== undefined);

        const card = mustQuery(main, '[data-group-key="SCD30"]');
        expect(card.dataset.applyStatus).toBe("invalid"); // worst-first across the whole group

        expect(mustQuery(card, '[data-field-wrapper-key="MeasInt"]').dataset.applyStatus).toBe("invalid");
        // Toggle/enum fields always resubmit their current, already-valid value - reads back
        // Unchanged, colored on their own box too, distinct from MeasInt's Invalid.
        expect(mustQuery(card, '[data-field-wrapper-key="ContMeas"]').dataset.applyStatus).toBe("unchanged");
        // COffset was never part of this submission at all (sparse-omitted) - no per-field result
        // to show, matching the legacy behavior this restores: only fields present in the
        // response's own result get colored.
        expect(mustQuery(card, '[data-field-wrapper-key="COffset"]').dataset.applyStatus).toBeUndefined();
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

    it("reports Invalid for non-numeric text in a composite subfield instead of silently submitting 0 (regression)", async () => {
        // Same NaN -> null -> 0 gap as the top-level number-field case above, but through
        // collectGroupBody()'s separate composite-field code path - r's min is 0, so a garbage
        // "r" that silently became 0 would otherwise pass.
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
        expect(card.dataset.applyStatus).toBe("invalid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("lightCmdLED: Invalid");
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
        // (SPECIFICATION.md Part A.8/A.5) - never a shaped HTTP error status. Before this fix,
        // render.js never checked envelope.res, so an empty `result` on this response silently
        // defaulted the whole card to "Valid" via applyResultStyling()'s own severity fallback.
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
        // Real server-side gap (WEBSITE_PLAN.md §10 session 3 follow-up 2): a settings group's
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
