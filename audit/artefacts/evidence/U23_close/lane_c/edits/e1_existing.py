import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text()
def sub(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)

# Fixture comment on the plain toggle.
sub('''                        // Deliberately not the real SCD30 key "ContMeas": mock-server.js
                        // special-cases that exact name for a hardware quirk (Part H.7), which
                        // this generic toggle-rendering fixture must stay clear of.
''', '''                        // A plain toggle: no dispatch or alwaysExecuted flag, so the mock stores and echoes it (SPECIFICATION.md Part H.4).
''')

# Helpers after answerGets().
sub('''/** @type {import("../js/definitions.js").SiteDefinitions} */
const DEFS = {''', '''/**
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
const DEFS = {''')

# Module-level fixtures after getSection().
sub('''const DATA = {
    measurements: {''', '''/**
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
    measurements: {''')

# The errcount group outside Status reads the captive DNS server's row.
sub('''            groups: [{ key: "dnsErrors", label: "Captive DNS Error History", kind: "errcount", modules: [{ key: "SCD30", label: "SCD30" }] }],
        };
        const defs = { ...DEFS, sections: [...DEFS.sections, section] };
        uninstall = installMockFetch(defs, DATA);
        const main = mount();
        stop = renderSection(defs, section, main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        mustQuery(main, ".action-button").click(); // "Show flagged"
        expect(mustQuery(mustQuery(main, ".errcount-row"), ".errcount-row-count").textContent).toBe("2");''', '''            groups: [{ key: "dnsErrors", label: "Captive DNS Error History", kind: "errcount", modules: [{ key: "DNSSRV", label: "Captive DNS" }] }],
        };
        const defs = { ...DEFS, sections: [...DEFS.sections, section] };
        const dnsHistory = [{ num: 3, type: /** @type {const} */ ("W") }];
        uninstall = installMockFetch(defs, { ...DATA, status: { ...DATA.status, errcount: { ...DATA.status.errcount, DNSSRV: { counter: 1, history: dnsHistory } } } });
        const main = mount();
        stop = renderSection(defs, section, main);
        await waitFor(() => main.querySelector(".errcount-rollup") !== null);

        mustQuery(main, ".action-button").click(); // "Show flagged"
        expect(mustQuery(main, ".errcount-row-name").textContent).toBe("Captive DNS");
        expect(mustQuery(mustQuery(main, ".errcount-row"), ".errcount-row-count").textContent).toBe("1");''')

sub('''        // Both real definitions files declare "status" as pollGroup "live" and this fixture's
        // DEFS deliberately does not, so exercising the poll-rebuild path needs a local variant -
        // the same pattern the live-polled readonly-field test above uses.
''', '''        // Every real device's Status section is live and this fixture's is not, so the poll-update path needs a local variant.
''')

# The reset: read from /status's per-field result, asked first, Off after Apply.
old_reset_start = s.index('''    it("shows Valid (not Failed) after a successful Reset All Errors submission''')
old_reset_end = s.index('''    describe("a toggle field with no real GET readback but a schema-declared defaultValue"''')
s = s[:old_reset_start] + '''    it("shows Valid after a successful Reset All Errors submission, read from /status's per-field result", async () => {
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

''' + s[old_reset_end:]

# The always-executed toggle replaces the retired defaultValue describe.
old_dv_start = s.index('''    describe("a toggle field with no real GET readback but a schema-declared defaultValue"''')
old_dv_end = s.index('''    it("skips the PUT and shows a neutral message when Apply is clicked with nothing to submit"''')
s = s[:old_dv_start] + '''    describe("an always-executed toggle with no GET value", () => {
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
            expect(toggle.textContent).toBe("\\u2014");

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

''' + s[old_dv_end:]

sub('''        // A group of only number/string fields can be genuinely empty when the visitor clicks
        // Apply without touching anything, and collectGroupBody() then returns {}. PUTing that
        // costs a round trip and shows applyResultStyling()'s empty-result "Valid" for nothing.
''', '''        // A group of only number/string fields can be genuinely empty when the visitor clicks
        // Apply without touching anything, and collectGroupBody() then returns {}: no round trip.
''')
sub('''        // No PUT was actually sent, so no outcome to color - the card must not claim a status
        // (particularly not the misleading "valid" an empty-result PUT response would produce).
''', '''        // No PUT was sent, so there is no outcome to colour.
''')

# The untouched SystemCmd test reads the module fixture.
old_sc_start = s.index('''    it("skips the PUT for an enum-only submit group (e.g. SystemCmd) left untouched''')
old_sc_mid = s.index('''        uninstall = installMockFetch(defsSystemCmd, DATA);''', old_sc_start)
s = s[:old_sc_start] + '''    it("skips the PUT for an enum-only submit group (e.g. SystemCmd) left untouched, instead of silently dispatching whichever command the browser defaults a bare <select> to (regression)", async () => {
        // SystemCmd is never returned by GET /system (SPECIFICATION.md A.8), so the select starts on its placeholder and an untouched Apply sends nothing.
        const defsSystemCmd = withSection(SYSTEM_SECTION);
''' + s[old_sc_mid:]
sub('''        const main = mount();
        const section = /** @type {import("../js/definitions.js").Section} */ (defsSystemCmd.sections.find((s) => s.key === "system"));
        stop = renderSection(defsSystemCmd, section, main);
        await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);''', '''        const main = mount();
        stop = renderSection(defsSystemCmd, SYSTEM_SECTION, main);
        await waitFor(() => main.querySelector('[data-field-key="SystemCmd"]') !== null);''')

# Non-numeric text: the comment follows the end state.
sub('''        // JSON.stringify(NaN) is "null", so typed garbage used to arrive as null and a
        // server-side Number(null) === 0 made it look like a deliberate in-range value.
        // COffset's min is 0 precisely so a min>0 rejection cannot pass this by accident.''', '''        // JSON.stringify(NaN) is "null"; the raw text is sent instead so the server can refuse it.
        // COffset's min is 0 precisely so a min>0 rejection cannot pass this by accident.''')

# LightCmdLED Valid clears its sub-inputs.
sub('''        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("LightCmdLED: Valid");
    });''', '''        const card = mustQuery(main, '[data-group-key="flash"]');
        expect(card.dataset.applyStatus).toBe("valid");
        expect(mustQuery(card, ".apply-result").textContent).toContain("LightCmdLED: Valid");
        // An accepted command's sub-inputs are cleared, so a second click cannot re-send it.
        await waitFor(() => [...grid.querySelectorAll("input")].every((input) => input.value === ""));
    });''')

# The PUT failure cases arm their failure for the PUT, past the GET an Apply sends first.
for failure in ('"network"', '"malformed-body"', '500', '"empty-body"'):
    sub(f'''        input.value = "10";
        controls.nextFailure = {failure};
        mustQuery(main, ".apply-button").click();''', f'''        input.value = "10";
        failNextPut(controls, {failure});
        mustQuery(main, ".apply-button").click();''')
p.write_text(s)
