// Server-side Vitest custom browser command (registered in vitest.config.js's
// `test.browser.commands`) backing tests_js/live-backend.test.js.
//
// Vitest browser mode's own `page` object (imported from "vitest/browser" inside a test) has no
// API for navigating to an arbitrary external origin - confirmed against vitest-dev/vitest#7875
// (open, unresolved) and the current commands/context docs, which only expose iframe-scoped
// helpers on the browser side. The supported escape hatch is the Commands API: a command function
// runs server-side (real Node, not the sandboxed browser context) and receives the *real*
// Playwright `BrowserContext` already launched for this test run, from which a genuine new page
// can be opened and navigated anywhere - exactly what's needed to drive the real, live digital
// twin (a full external HTTP server, not anything Vitest's own dev server is serving).
//
// This file does the whole live-backend round trip itself (spawn the twin, wait for it to serve,
// drive a real page against it, tear down) rather than splitting the work across several
// browser<->server RPC calls, since the subprocess/Playwright-navigation work is all server-side
// anyway - only the final serializable result crosses back to the test.

import { spawn } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
const MICROPYPATH = "src:digital_twin:ext:frozen_modules:.frozen";
const HOST = "127.0.0.1";
// Distinct from every other fixed port this repo already uses for a twin/integration run (8080
// manual walkthrough, 18080 Python's own automated CI suite, 19300+ Python's
// test_digital_twin_sensortask_integration.py/test_digital_twin_real_website_integration.py) -
// see digital_twin/README.md's "never together" note. This one's launched from Node, not Python,
// so there's no real collision risk either way, but a distinct value keeps every entry point's
// port trivially attributable from a process listing alone.
const PORT = 19411;
const READY_TIMEOUT_MS = 20000;
const SHUTDOWN_TIMEOUT_MS = 15000;

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
        [
            "digital_twin/run_wozi_integration.py",
            "--host",
            HOST,
            "--port",
            String(PORT),
            "--fram-state-path",
            "", // in-memory only - see digital_twin/README.md's "FRAM persistence" section for this convention
            "--scd30-state-path",
            "", // same convention, "SCD30 persistence" section
        ],
        {
            cwd: REPO_ROOT,
            env: { ...process.env, MICROPYPATH, TZ: "UTC" },
            // stdout: ignored (never read) - an unconsumed piped stream keeps Node's event loop
            // alive (and can eventually block the child if its OS pipe buffer fills), which is
            // exactly what left the vitest process hanging on exit before this was "ignore".
            // stderr: piped and drained below, only for surfacing into a failure's error message.
            stdio: ["ignore", "ignore", "pipe"],
        },
    );
    // An unhandled ChildProcess 'error' event (e.g. a spawn failure) crashes the whole Node/Vitest
    // process synchronously, skipping this file's own try/finally cleanup entirely - confirmed as a
    // real gap (pre-merge audit). A no-op listener is enough: it just prevents the crash: the
    // existing waitUntilServing()/goto() error paths already surface a spawn failure via their own
    // timeouts.
    proc.on("error", () => {});
    return proc;
}

/** @param {import("node:child_process").ChildProcess} proc */
async function stopTwin(proc) {
    if (proc.exitCode !== null || proc.signalCode !== null) {
        return;
    }
    // SIGINT, not SIGTERM/kill('SIGTERM'): run_wozi_integration.py's own graceful-shutdown path
    // (FRAM/SCD30 flush) only runs on KeyboardInterrupt - a plain SIGTERM would skip it, same
    // reasoning as scripts/_digital_twin_ci_suite.py's own _shutdown().
    proc.kill("SIGINT");
    await Promise.race([
        new Promise((resolve) => {
            proc.once("exit", resolve);
        }),
        sleep(SHUTDOWN_TIMEOUT_MS).then(() => proc.kill("SIGKILL")),
    ]);
}

/**
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, titleHasSensorStation: boolean, deviceName: string, debugLevelApplyStatus: string | null}>}
 */
export async function runLiveBackendSmoke({ context }) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return {
            skipped: true,
            reason: `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`,
        };
    }

    // Fresh state every run, mirroring scripts/_digital_twin_ci_suite.py's own "clean" step -
    // FRAM/SCD30 are already in-memory-only above; config/ is the one thing that still persists
    // to a fixed path by default (run_wozi_integration.py exposes no --cfg-path flag).
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    const proc = spawnTwin();
    let stderr = "";
    proc.stderr?.on("data", (/** @type {Buffer} */ chunk) => {
        stderr += chunk.toString();
    });

    let livePage;
    try {
        await waitUntilServing(READY_TIMEOUT_MS);

        livePage = await context.newPage();
        const consoleMessages = [];
        livePage.on("console", (msg) => consoleMessages.push(`[console:${msg.type()}] ${msg.text()}`));
        livePage.on("pageerror", (err) => consoleMessages.push(`[pageerror] ${err.message}`));
        const gotoRes = await livePage.goto(`http://${HOST}:${PORT}/`);
        consoleMessages.push(`[goto] status=${gotoRes?.status()} url=${gotoRes?.url()}`);
        try {
            await livePage.waitForSelector('[data-section-key="system"]', { timeout: 10000 });
        } catch (err) {
            const html = await livePage.content();
            throw new Error(`${err instanceof Error ? err.message : String(err)}\n--- console ---\n${consoleMessages.join("\n")}\n--- html (first 2000 chars) ---\n${html.slice(0, 2000)}`, { cause: err });
        }

        const titleHasSensorStation = (await livePage.title()).includes("Sensor Station");
        const deviceName = (await livePage.locator("#device-name").textContent())?.trim() ?? "";

        // The nav is a slide-in drawer (SPECIFICATION.md Part H.4), off-screen/hidden until the
        // hamburger button opens it - the section links exist in the DOM immediately (confirmed
        // above via waitForSelector) but aren't clickable until the drawer is actually open.
        await livePage.locator("#hamburger-button").click();
        await livePage.locator('[data-section-key="system"]').click();
        const debugLevelInput = livePage.locator('[data-field-key="DebugLevel"]');
        await debugLevelInput.waitFor();
        await debugLevelInput.fill("4");
        const card = livePage.locator("[data-group-key]").filter({ has: debugLevelInput });
        await card.locator(".apply-button").click();

        const fieldWrapper = livePage.locator('[data-field-wrapper-key="DebugLevel"]');
        let debugLevelApplyStatus = null;
        const attrDeadline = Date.now() + 10000;
        while (debugLevelApplyStatus === null && Date.now() < attrDeadline) {
            // eslint-disable-next-line no-await-in-loop -- deliberate sequential polling
            debugLevelApplyStatus = await fieldWrapper.getAttribute("data-apply-status");
            if (debugLevelApplyStatus === null) {
                // eslint-disable-next-line no-await-in-loop -- same reasoning as above
                await sleep(200);
            }
        }

        return { skipped: false, titleHasSensorStation, deviceName, debugLevelApplyStatus };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        throw new Error(`live-backend smoke check failed: ${message}\n--- twin stderr ---\n${stderr}`, { cause: err });
    } finally {
        if (livePage) {
            livePage.removeAllListeners();
            await livePage.close().catch(() => {});
        }
        await stopTwin(proc);
    }
}
