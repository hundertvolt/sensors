// Server-side Vitest Commands API module backing tests_js/live-backend-put-matrix.test.js: a
// shared, boot-once-per-file live digital-twin + real-browser harness driving many real UI
// actions against one real backend. See SPECIFICATION.md Part H.7.
import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expectedDisplay } from "./_expected_display.js";
import { drainChildOutput } from "./_memory_markers.js";
import { HOST, READY_TIMEOUT_MS, SHUTDOWN_TIMEOUT_MS, makeConfigDir, removeConfigDir, requireInterpreter, sleep, spawnTwin, stopTwin, twinVerdict, waitUntilServing } from "./_twin_process.js";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// Clear of every fixed port this repo binds - see tests_js/_live_twin_command.js's own PORT comment;
// this harness's twin runs alongside that file's (19481) in one `npm test` run.
const PORT = 19482;
// @tunable l0.put_matrix_apply_status_timeout_ms = 5000
const APPLY_STATUS_TIMEOUT_MS = 5000;
// Generous bound for pollForText() - see SPECIFICATION.md Part H.8.1 ("Testing an async DOM refresh").
// @tunable l0.put_matrix_caption_poll_timeout_ms = 3000
const CAPTION_POLL_TIMEOUT_MS = 3000;

/** @type {import("node:child_process").ChildProcess | null} */
let twinProc = null;
/** @type {ReturnType<typeof drainChildOutput> | null} */
let twinOutput = null;
/** @type {import("playwright").Page | null} */
let livePage = null;
/** @type {string | null} */
let archiveRunDir = null;
/** @type {string | null} */
let twinConfigDir = null; // the matrix twin's own config directory, removed once it stopped

/** Removes the matrix twin's config directory once the twin has stopped. */
function dropConfigDir() {
    if (twinConfigDir !== null) {
        removeConfigDir(twinConfigDir);
        twinConfigDir = null;
    }
}

/**
 * The matrix's run settings, read without booting a twin: the shard $PUT_MATRIX_SHARD selects, once the interpreter
 * is known to be built (a missing one fails the file, never skips it). It travels back through the Commands API
 * because the test runs in the browser, where process.env does not exist (SPECIFICATION.md Part H.7).
 * @returns {{shard: string}}
 */
export function getLiveMatrixConfig() {
    requireInterpreter();
    return { shard: process.env.PUT_MATRIX_SHARD ?? "" };
}

/**
 * Boots `device`'s twin and opens/navigates one real page. Every later command in this module
 * operates against that same twin/page until stopLiveMatrix() tears it down, so devices run one
 * after another on PORT.
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @param {string} device a devices/<device>.toml stem
 * @returns {Promise<void>}
 */
export async function startLiveMatrix({ context }, device) {
    twinConfigDir = makeConfigDir();
    twinProc = spawnTwin({ device, port: PORT, configDir: twinConfigDir });
    const output = drainChildOutput(twinProc);
    twinOutput = output;

    try {
        await waitUntilServing(twinProc, PORT, READY_TIMEOUT_MS);
        livePage = await context.newPage();
        // The drawer then opens without its 0.18 s slide (style.css drops only that), so a nav click does not wait the
        // slide out to find its link stable; every check of the page stays as it was.
        await livePage.emulateMedia({ reducedMotion: "reduce" });
        await livePage.goto(`http://${HOST}:${PORT}/`);
        await livePage.waitForSelector("[data-section-key]");
    } catch (err) {
        // A failure here means the test file's top-level startLiveMatrix() threw before its
        // afterAll(stopLiveMatrix) was ever registered. Without tearing down right here, a slow
        // page load orphans the twin and pins PORT until someone kills it by hand.
        if (livePage) {
            await livePage.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
            // eslint-disable-next-line require-atomic-updates -- see stopLiveMatrix()'s own comment below
            livePage = null;
        }
        if (twinProc) {
            await stopTwin(twinProc);
            // eslint-disable-next-line require-atomic-updates -- see stopLiveMatrix()'s own comment below
            twinProc = null;
        }
        dropConfigDir();
        twinOutput = null;
        twinVerdict(`startLiveMatrix for ${device}`, [output], err, await output.closed(SHUTDOWN_TIMEOUT_MS));
        throw err; // not reached: the verdict throws for every failure
    }
}

// require-atomic-updates flags livePage/twinProc as read-then-written across an await, which is
// unsafe only under concurrent invocation. Vitest dispatches Commands API calls strictly
// sequentially from one file's await chain, so the race the rule guards cannot happen.
export async function stopLiveMatrix() {
    if (livePage) {
        await livePage.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
        // eslint-disable-next-line require-atomic-updates -- see comment above
        livePage = null;
    }
    if (twinProc) {
        await stopTwin(twinProc);
        // eslint-disable-next-line require-atomic-updates -- see comment above
        twinProc = null;
    }
    dropConfigDir();
    const output = twinOutput;
    twinOutput = null;
    // The run's memory gate (SPECIFICATION.md Part I.4(e)): read once the twin has stopped and its
    // streams have closed, so the whole matrix fails on a marker even when every field applied.
    if (output !== null) {
        twinVerdict("the live matrix", [output], null, await output.closed(SHUTDOWN_TIMEOUT_MS));
    }
}

/**
 * Raw HTTP GETs straight against the twin (bypassing the browser entirely) - the real baseline
 * every matrix case is generated against, the live-backend equivalent of
 * tests_js/mock-server-put-matrix.test.js's own `mockdata/*.json` fixtures.
 * @param {import("playwright").BrowserContext} _context unused - every command here still declares
 * this leading parameter since Vitest's BrowserCommand type always calls `(context, ...payload)`.
 * @param {string[]} paths e.g. ["/sensors", "/networking", "/system", "/notification", "/status"]
 * @returns {Promise<Record<string, unknown>>} keyed by path
 */
export async function getRealCurrentValues(_context, paths) {
    /** @type {Record<string, unknown>} */
    const out = {};
    for (const p of paths) {
        // eslint-disable-next-line no-await-in-loop -- small, fixed, sequential set of real endpoints
        const res = await fetch(`http://${HOST}:${PORT}${p}`);
        if (!res.ok) {
            throw new Error(`GET ${p} -> HTTP ${res.status}`);
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        const body = await res.json();
        // A GET answers its bare data object; an envelope (it carries `res`) is an error the baseline must not absorb.
        if (typeof body !== "object" || body === null || Array.isArray(body) || "res" in body) {
            throw new Error(`GET ${p} did not answer a data object`);
        }
        out[p] = body;
    }
    return out;
}

/**
 * Saves GET /status's `errcount` verbatim under build/archive/live_twin/ (scripts/_archive_evidence.py) before a
 * case resets it, so the evidence a reset clears outlives the run.
 * @param {import("playwright").BrowserContext} _context unused - see getRealCurrentValues()'s own note.
 * @param {string} label names the saved file, e.g. the device and the step
 * @returns {Promise<string>} the archived file's path
 */
export async function archiveErrcount(_context, label) {
    const { "/status": status } = await getRealCurrentValues(_context, ["/status"]);
    // One run directory per test process: every device's counts of one run sit together, and the archive's keep-3
    // pruning counts runs, never the devices of the run in progress.
    archiveRunDir ??= execFileSync("uv", ["run", "--quiet", "scripts/_archive_evidence.py", "--runner", "live_twin", "--new-dir"], { cwd: REPO_ROOT, encoding: "utf8" }).trim();
    if (archiveRunDir === "") {
        throw new Error("archiveErrcount: scripts/_archive_evidence.py made no run directory");
    }
    const file = path.join(archiveRunDir, `errcount-${label.replace(/[^a-z0-9_-]/giu, "_")}.json`);
    writeFileSync(file, `${JSON.stringify(/** @type {{errcount?: unknown}} */ (status).errcount ?? null, null, 2)}\n`);
    return file;
}

/** @param {boolean} open */
async function setDrawerOpen(open) {
    const hamburger = /** @type {import("playwright").Page} */ (livePage).locator("#hamburger-button");
    const expanded = (await hamburger.getAttribute("aria-expanded")) === "true";
    if (expanded !== open) {
        await hamburger.click();
    }
}

/**
 * Resolves on the first frame `locator`'s element is visible as a locator's waitFor judges it, and enabled when asked:
 * that waitFor checks at steps growing to 0.5 s, so it idled up to that long after each paint it waited for.
 * @param {import("playwright").Locator} locator one element already in the page
 * @param {{enabled?: boolean, timeout?: number}} [options] the page's default timeout when none is given
 */
async function onFrameShown(locator, { enabled = false, timeout } = {}) {
    const limit = timeout === undefined ? {} : { timeout };
    const handle = await locator.elementHandle(limit);
    try {
        await locator.page().waitForFunction(([el, wantEnabled]) => {
            if (!el.isConnected || !el.checkVisibility() || el.ownerDocument.defaultView?.getComputedStyle(el).visibility !== "visible") {
                return false;
            }
            const box = el.getBoundingClientRect();
            return box.width > 0 && box.height > 0 && (!wantEnabled || el.matches(":enabled"));
        }, /** @type {const} */ ([handle, enabled]), limit);
    } catch (err) {
        throw new Error(`${String(locator)} was not shown${enabled ? " and enabled" : ""} in time`, { cause: err });
    } finally {
        await handle.dispose();
    }
}

/**
 * Navigates to `sectionKey` via a real drawer-open + nav-link click, exactly like a visitor would -
 * always a genuine click, even when already on that section (js/shell.js's selectSection() always
 * tears down and rebuilds fresh regardless), which is exactly what a from-scratch render check needs.
 * @param {string} sectionKey
 */
async function navigateToSection(sectionKey) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    await setDrawerOpen(true);
    await page.locator(`[data-section-key="${sectionKey}"]`).click();
    await onFrameShown(page.locator(".group-grid"));
    await page.locator(".group-grid").waitFor();
}

/**
 * Clicks a toggle until its `data-value` reads `desired`: at most two clicks, from any of its three states.
 * @param {import("playwright").Locator} control
 * @param {string} desired "true" or "false"
 */
async function setToggle(control, desired) {
    for (let clicks = 0; ; clicks += 1) {
        // eslint-disable-next-line no-await-in-loop -- each click changes what the next read sees
        const current = await control.getAttribute("data-value");
        if (current === desired) {
            return;
        }
        if (clicks === 2) {
            throw new Error(`the toggle still reads ${String(current)} after two clicks, not ${desired}`);
        }
        // eslint-disable-next-line no-await-in-loop -- as above
        await control.click();
    }
}

/**
 * Clicks the card's Apply and waits until the button is enabled again (the PUT and its post-write GET finished),
 * accepting exactly the one confirmation `confirmMessage` names and failing on any other dialog.
 * @param {import("playwright").Locator} card
 * @param {string | undefined} confirmMessage
 * @returns {Promise<string>} the card's `data-apply-status`
 */
async function applyAndSettle(card, confirmMessage) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    /** @type {string[]} */
    const unexpected = [];
    let confirmed = false;
    /** @param {import("playwright").Dialog} dialog */
    const onDialog = async (dialog) => {
        if (!confirmed && dialog.type() === "confirm" && dialog.message() === confirmMessage) {
            confirmed = true;
            await dialog.accept();
        } else {
            unexpected.push(`${dialog.type()} "${dialog.message()}"`);
            await dialog.dismiss();
        }
    };
    page.on("dialog", onDialog);
    try {
        await card.locator(".apply-button").click();
        await onFrameShown(card.locator(".apply-button"), { enabled: true, timeout: APPLY_STATUS_TIMEOUT_MS });
        await card.locator(".apply-button:enabled").waitFor({ timeout: APPLY_STATUS_TIMEOUT_MS });
    } finally {
        page.off("dialog", onDialog);
    }
    if (unexpected.length > 0) {
        throw new Error(`Apply raised a dialog no field asked for: ${unexpected.join(", ")}`);
    }
    if (confirmMessage !== undefined && !confirmed) {
        throw new Error(`Apply never asked "${confirmMessage}"`);
    }
    const status = await card.getAttribute("data-apply-status");
    if (status === null) {
        throw new Error(`the card has no data-apply-status once Apply settled: ${String(await card.locator(".apply-result").textContent())}`);
    }
    return status;
}

/**
 * Polls `locator`'s text content until it equals `expectedText` or `timeoutMs` elapses, returning
 * whatever's there either way. See SPECIFICATION.md Part H.8.1 ("Testing an async DOM refresh")
 * for why this polls instead of using a fixed sleep.
 * @param {import("playwright").Locator} locator
 * @param {string} expectedText
 * @param {number} timeoutMs
 * @returns {Promise<string | null>}
 */
async function pollForText(locator, expectedText, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    /** @type {string | null} */
    let last = null;
    while (Date.now() < deadline) {
        // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
        last = await locator.textContent();
        if (last === expectedText) {
            return last;
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(50);
    }
    return last;
}

/**
 * Fills one field's real control with `value` (per its real `kind`), clicks its card's Apply, answers the field's
 * confirmation and waits for the Apply to finish; then, for a number/string, polls its caption for the text
 * `expectRenderedValue` should show (the applied value when the device took it, its untouched value when refused).
 * @param {import("playwright").BrowserContext} _context unused - every command here still declares
 * this leading parameter since Vitest's BrowserCommand type always calls `(context, ...payload)`.
 * @param {{
 *   sectionKey: string, groupKey: string, fieldKey: string, field: import("./_expected_display.js").DisplayField,
 *   value: unknown, expectRenderedValue: unknown, defaultDecimals?: number, confirmMessage?: string, readCaption?: boolean,
 * }} args `readCaption: false` skips the caption, for a field whose caption shows a live state, not the sent value
 * @returns {Promise<{applyStatus: string, captionText: string | null, toggleValue: string | null, selectValue: string | null}>}
 */
export async function applyField(_context, { sectionKey, groupKey, fieldKey, field, value, expectRenderedValue, defaultDecimals, confirmMessage, readCaption = true }) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    const { kind } = field;
    await navigateToSection(sectionKey);
    const card = page.locator(`[data-group-key="${groupKey}"]`);
    await card.waitFor();
    const control = card.locator(`[data-field-key="${fieldKey}"]`);

    if (kind === "number" || kind === "string") {
        await control.fill(String(value));
    } else if (kind === "toggle") {
        await setToggle(control, String(Boolean(value)));
    } else if (kind === "enum") {
        await control.selectOption({ value: String(value) });
    } else if (kind === "composite") {
        for (const [subKey, subValue] of Object.entries(/** @type {Record<string, unknown>} */ (value))) {
            // eslint-disable-next-line no-await-in-loop -- one sub-input after another, as a visitor fills them
            await control.locator(`[data-sub-field-key="${subKey}"]`).fill(String(subValue));
        }
    } else {
        throw new Error(`applyField: a ${kind} field has no control to fill`);
    }

    const applyStatus = await applyAndSettle(card, confirmMessage);
    let captionText = null;
    if (readCaption && (kind === "number" || kind === "string")) {
        const expectedCaption = `Current value: ${expectedDisplay(field, expectRenderedValue, defaultDecimals)}`;
        captionText = await pollForText(card.locator(`[data-current-value-for="${fieldKey}"]`), expectedCaption, CAPTION_POLL_TIMEOUT_MS);
    }
    const toggleValue = kind === "toggle" ? await control.getAttribute("data-value") : null;
    const selectValue = kind === "enum" ? await control.inputValue() : null;
    return { applyStatus, captionText, toggleValue, selectValue };
}

/**
 * Leaves a non-dispatch toggle/enum at its current value and clicks Apply, expecting collectGroupBody() to
 * sparse-omit it: no PUT fires, so no status is waited on.
 * @param {import("playwright").BrowserContext} _context unused - see applyField()'s own note.
 * @param {{sectionKey: string, groupKey: string, fieldKey: string, kind: "toggle" | "enum", value: unknown}} args
 * @returns {Promise<{resultText: string | null, applyStatus: string | null}>}
 */
export async function applyUnchangedFieldExpectNothingToSubmit(_context, { sectionKey, groupKey, fieldKey, kind, value }) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    await navigateToSection(sectionKey);
    const card = page.locator(`[data-group-key="${groupKey}"]`);
    await card.waitFor();
    const control = card.locator(`[data-field-key="${fieldKey}"]`);

    if (kind === "toggle") {
        await setToggle(control, String(Boolean(value)));
    } else {
        await control.selectOption({ value: String(value) });
    }

    await card.locator(".apply-button").click();
    const resultText = await pollForText(card.locator(".apply-result"), "Nothing to submit - no fields were changed.", APPLY_STATUS_TIMEOUT_MS);
    const applyStatus = await card.getAttribute("data-apply-status");
    return { resultText, applyStatus };
}

/**
 * Remounts `sectionKey` and reads `fieldKey`'s freshly built control, whose value comes from the remount's own GET,
 * not the page's own state (SPECIFICATION.md Part H.3); a readonly field gives its shown text, and kind "errcount"
 * every row of the shown group, unremounted, as "<module>: <count>".
 * @param {import("playwright").BrowserContext} _context unused - every command here still declares
 * this leading parameter since Vitest's BrowserCommand type always calls `(context, ...payload)`.
 * @param {{sectionKey: string, groupKey: string, fieldKey: string, kind: string}} args
 * @returns {Promise<{placeholder: string | null, toggleValue: string | null, toggleText: string | null, selectValue: string | null, valueText: string | null, errcountRows: string[]}>}
 */
export async function remountAndReadField(_context, { sectionKey, groupKey, fieldKey, kind }) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    const read = { placeholder: null, toggleValue: null, toggleText: null, selectValue: null, valueText: null, errcountRows: [] };
    if (kind === "errcount") {
        // In place, as the shown section's last poll painted them, so the read adds no request of its own.
        const rows = page.locator(`[data-group-key="${groupKey}"] .errcount-row`);
        await rows.first().waitFor({ state: "attached" });
        const texts = () => rows.evaluateAll((elements) => elements.map((row) => `${row.querySelector(".errcount-row-name")?.textContent ?? "?"}: ${row.querySelector(".errcount-row-count")?.textContent ?? "?"}`));
        return { ...read, errcountRows: await texts() };
    }
    await navigateToSection(sectionKey);
    const card = page.locator(`[data-group-key="${groupKey}"]`);
    await card.waitFor();
    const control = card.locator(`[data-field-key="${fieldKey}"]`);
    await control.waitFor();

    if (kind === "number" || kind === "string") {
        return { ...read, placeholder: await control.getAttribute("placeholder") };
    }
    if (kind === "toggle") {
        return { ...read, toggleValue: await control.getAttribute("data-value"), toggleText: await control.textContent() };
    }
    if (kind === "enum") {
        return { ...read, selectValue: await control.inputValue() };
    }
    if (kind === "readonly") {
        return { ...read, valueText: await control.textContent() };
    }
    throw new Error(`remountAndReadField: unsupported kind "${kind}"`);
}
