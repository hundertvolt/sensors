// Server-side Vitest Commands API module backing tests_js/live-backend-put-matrix.test.js: a
// shared, boot-once-per-file live digital-twin + real-browser harness driving many real UI
// actions against one real backend. See SPECIFICATION.md Part H.7.
import { spawn } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
// Reused (not hand-duplicated) so this module knows the *exact* expected caption text to poll for
// below - see SPECIFICATION.md Part H.8.1 for why this is a DOM-free module, not a
// js/templates.js import.
import { formatFieldValue } from "../js/field-format.js";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
const MICROPYPATH = "src:digital_twin:ext:frozen_modules:.frozen";
const HOST = "127.0.0.1";
// Distinct from every other fixed port this repo uses - see tests_js/_live_twin_command.js's own
// PORT comment for the full list; this harness's twin runs alongside that file's in one `npm test` run.
const PORT = 19412;
const READY_TIMEOUT_MS = 20000;
const SHUTDOWN_TIMEOUT_MS = 15000;
const APPLY_STATUS_TIMEOUT_MS = 5000;
// Generous bound for pollForText() - see SPECIFICATION.md Part H.8.1 ("Testing an async DOM refresh").
const CAPTION_POLL_TIMEOUT_MS = 3000;

/** @param {number} ms */
function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/** @param {number} timeoutMs */
async function waitUntilServing(timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        try {
            // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
            const res = await fetch(`http://${HOST}:${PORT}/`);
            if (res.status === 200) {
                return;
            }
        } catch {
            // Not up yet - keep polling.
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(250);
    }
    throw new Error(`digital twin never started serving on ${HOST}:${PORT} within ${timeoutMs}ms`);
}

function spawnTwin() {
    const proc = spawn(
        MICROPYTHON_BIN,
        ["digital_twin/run_wozi_integration.py", "--host", HOST, "--port", String(PORT), "--fram-state-path", "", "--scd30-state-path", ""],
        {
            cwd: REPO_ROOT,
            env: { ...process.env, MICROPYPATH, TZ: "UTC" },
            // Same reasoning as tests_js/_live_twin_command.js's own stdio choice - see that
            // file's own comment.
            stdio: ["ignore", "ignore", "pipe"],
        },
    );
    // See tests_js/_live_twin_command.js's own identical comment: an unhandled 'error' event would
    // otherwise crash the whole Vitest process, skipping this file's own cleanup entirely.
    proc.on("error", () => {});
    return proc;
}

/** @param {import("node:child_process").ChildProcess} proc */
async function stopTwin(proc) {
    if (proc.exitCode !== null || proc.signalCode !== null) {
        return;
    }
    proc.kill("SIGINT"); // graceful shutdown path - see tests_js/_live_twin_command.js's own comment
    await Promise.race([
        new Promise((resolve) => {
            proc.once("exit", resolve);
        }),
        sleep(SHUTDOWN_TIMEOUT_MS).then(() => proc.kill("SIGKILL")),
    ]);
}

/** @type {import("node:child_process").ChildProcess | null} */
let twinProc = null;
let twinStderr = "";
/** @type {import("playwright").Page | null} */
let livePage = null;

/**
 * Boots the twin and opens/navigates one real page, once for the whole test file. Every later
 * command in this module operates against that same twin/page until stopLiveMatrix() tears it down.
 * @param {{context: import("playwright").BrowserContext}} ctx
 */
export async function startLiveMatrix({ context }) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return {
            skipped: true,
            reason: `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`,
        };
    }
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    twinProc = spawnTwin();
    twinStderr = "";
    twinProc.stderr?.on("data", (/** @type {Buffer} */ chunk) => {
        twinStderr += chunk.toString();
    });

    try {
        await waitUntilServing(READY_TIMEOUT_MS);
        livePage = await context.newPage();
        await livePage.goto(`http://${HOST}:${PORT}/`);
        await livePage.waitForSelector("[data-section-key]");
        return { skipped: false };
    } catch (err) {
        // A failure here means the test file's top-level `await commands.startLiveMatrix()` throws
        // before its own afterAll(() => commands.stopLiveMatrix()) is ever registered - without
        // tearing the twin down right here, a boot failure (a slow/flaky page load, most commonly)
        // orphans the twin subprocess for the rest of the process's lifetime, pinning PORT for
        // every subsequent run until someone manually kills it.
        if (livePage) {
            await livePage.close().catch(() => {});
            // eslint-disable-next-line require-atomic-updates -- see stopLiveMatrix()'s own comment below
            livePage = null;
        }
        if (twinProc) {
            await stopTwin(twinProc);
            // eslint-disable-next-line require-atomic-updates -- see stopLiveMatrix()'s own comment below
            twinProc = null;
        }
        const message = err instanceof Error ? err.message : String(err);
        throw new Error(`startLiveMatrix failed: ${message}\n--- twin stderr ---\n${twinStderr}`, { cause: err });
    }
}

// require-atomic-updates flags livePage/twinProc as read-then-written across an await, which is
// only unsafe under concurrent invocation - Vitest's Commands API calls are dispatched strictly
// sequentially by one test file's own await chain (never two in flight at once against this
// module), so the actual race the rule guards against can't happen here.
export async function stopLiveMatrix() {
    if (livePage) {
        await livePage.close().catch(() => {});
        // eslint-disable-next-line require-atomic-updates -- see comment above
        livePage = null;
    }
    if (twinProc) {
        await stopTwin(twinProc);
        // eslint-disable-next-line require-atomic-updates -- see comment above
        twinProc = null;
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
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        out[p] = await res.json();
    }
    return out;
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
 * Navigates to `sectionKey` via a real drawer-open + nav-link click, exactly like a visitor would -
 * always a genuine click, even when already on that section (js/main.js's selectSection() always
 * tears down and rebuilds fresh regardless), which is exactly what a from-scratch render check needs.
 * @param {string} sectionKey
 */
async function navigateToSection(sectionKey) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    await setDrawerOpen(true);
    await page.locator(`[data-section-key="${sectionKey}"]`).click();
    await page.locator(".group-grid").waitFor();
}

/**
 * @param {import("playwright").Locator} card
 * @param {number} timeoutMs
 * @returns {Promise<string>}
 */
async function waitForApplyStatus(card, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
        const status = await card.getAttribute("data-apply-status");
        if (status) {
            return status;
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(50);
    }
    throw new Error(`card never got a data-apply-status within ${timeoutMs}ms`);
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
 * Fills one field's real control with `value` (per its real `kind`) and clicks its group card's
 * real Apply button - the same gesture tests_js/live-backend.test.js's single DebugLevel case
 * drives, generalized to every writable field kind.
 * @param {import("playwright").BrowserContext} _context unused - every command here still declares
 * this leading parameter since Vitest's BrowserCommand type always calls `(context, ...payload)`.
 * @param {{
 *   sectionKey: string, groupKey: string, fieldKey: string,
 *   field: import("../js/field-format.js").FormattableField, value: unknown, expectRenderedValue: unknown,
 * }} args `expectRenderedValue` is what the caller expects rendered afterward - the applied `value`
 * when it should be accepted, or the field's own untouched current value when it should be
 * rejected - so this command always knows the exact text to poll for (see pollForText()).
 * @returns {Promise<{applyStatus: string, captionText: string | null, toggleValue: string | null, selectValue: string | null}>}
 */
export async function applyField(_context, { sectionKey, groupKey, fieldKey, field, value, expectRenderedValue }) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    const kind = field.kind;
    await navigateToSection(sectionKey);
    const card = page.locator(`[data-group-key="${groupKey}"]`);
    await card.waitFor();
    const control = card.locator(`[data-field-key="${fieldKey}"]`);

    if (kind === "number" || kind === "string") {
        await control.fill(String(value));
    } else if (kind === "toggle") {
        const desired = String(Boolean(value));
        const current = await control.getAttribute("data-value");
        if (current !== desired) {
            await control.click();
        }
    } else if (kind === "enum") {
        await control.selectOption({ value: String(value) });
    } else {
        throw new Error(`applyField: unsupported kind "${kind}" - composite/readonly/dispatch-only fields aren't driven through this generic matrix (see SPECIFICATION.md Part H.7)`);
    }

    await card.locator(".apply-button").click();
    const applyStatus = await waitForApplyStatus(card, APPLY_STATUS_TIMEOUT_MS);

    let captionText = null;
    if (kind === "number" || kind === "string") {
        const captionLocator = card.locator(`[data-current-value-for="${fieldKey}"]`);
        const expectedCaption = `Current value: ${formatFieldValue(field, expectRenderedValue)}`;
        captionText = await pollForText(captionLocator, expectedCaption, CAPTION_POLL_TIMEOUT_MS);
    } else {
        // Toggle/select never self-refresh in place (SPECIFICATION.md Part H.3) - the control's current
        // state IS this action's own synchronous DOM write, just worth a short event-loop beat.
        await sleep(50);
    }
    const toggleValue = kind === "toggle" ? await control.getAttribute("data-value") : null;
    const selectValue = kind === "enum" ? await control.inputValue() : null;

    return { applyStatus, captionText, toggleValue, selectValue };
}

/**
 * Forces a genuinely fresh remount of `sectionKey` and reads back `fieldKey`'s freshly-rendered
 * initial state - the only real-UI-driven proof a toggle/enum field's persisted value round-tripped
 * (SPECIFICATION.md Part H.3: an in-place poll never touches those controls).
 * @param {import("playwright").BrowserContext} _context unused - every command here still declares
 * this leading parameter since Vitest's BrowserCommand type always calls `(context, ...payload)`.
 * @param {{sectionKey: string, groupKey: string, fieldKey: string, kind: string}} args
 * @returns {Promise<{placeholder: string | null, toggleValue: string | null, toggleText: string | null, selectValue: string | null}>}
 */
export async function remountAndReadField(_context, { sectionKey, groupKey, fieldKey, kind }) {
    const page = /** @type {import("playwright").Page} */ (livePage);
    await navigateToSection(sectionKey);
    const card = page.locator(`[data-group-key="${groupKey}"]`);
    await card.waitFor();
    const control = card.locator(`[data-field-key="${fieldKey}"]`);
    await control.waitFor();

    if (kind === "number" || kind === "string") {
        return { placeholder: await control.getAttribute("placeholder"), toggleValue: null, toggleText: null, selectValue: null };
    }
    if (kind === "toggle") {
        return { placeholder: null, toggleValue: await control.getAttribute("data-value"), toggleText: await control.textContent(), selectValue: null };
    }
    if (kind === "enum") {
        return { placeholder: null, toggleValue: null, toggleText: null, selectValue: await control.inputValue() };
    }
    throw new Error(`remountAndReadField: unsupported kind "${kind}"`);
}
