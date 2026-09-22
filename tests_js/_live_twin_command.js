// Server-side Vitest Commands API module backing tests_js/live-backend.test.js: spawns the twin
// and drives a real Playwright page against it directly (Vitest's own browser-mode `page` has no
// API for navigating to an external origin - vitest-dev/vitest#7875). See SPECIFICATION.md Part H.7.

import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TOOLCHAIN_DIR = process.env.PICO_TOOLCHAIN_DIR || path.join(homedir(), "pico-toolchain");
const MICROPYTHON_BIN = path.join(TOOLCHAIN_DIR, "micropython", "ports", "unix", "build-standard", "micropython");
// build/generated_src first: no static src/sensortask_wozi.py exists any more
// (SPECIFICATION.md Part L.2) - package.json's own "pretest"/
// "pretest:coverage" hooks generate it fresh there, via buildgen, before this spawns.
const MICROPYPATH = "build/generated_src:src:digital_twin:ext:frozen_modules:.frozen";
const HOST = "127.0.0.1";
// Distinct from every other fixed twin/integration port here (8080, 18080, 19300+ - see
// digital_twin/README.md's "never together" note). Launched from Node rather than Python, so
// there is no real collision risk; a distinct value just keeps a process listing attributable.
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
            "digital_twin/run_generic_integration.py",
            "--module",
            "sensortask_wozi",
            "--wiring-plan",
            path.join(REPO_ROOT, "build", "generated_src", "sensortask_wozi_wiring_plan.json"),
            "--device",
            "wozi",
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
            // stdout ignored rather than piped: an unconsumed pipe keeps Node's event loop alive
            // and can block the child once its buffer fills, hanging vitest at exit. stderr is
            // piped and drained below, only to surface in a failure's error message.
            stdio: ["ignore", "ignore", "pipe"],
        },
    );
    // An unhandled ChildProcess 'error' event crashes the whole Node/Vitest process
    // synchronously, skipping this file's try/finally entirely. A no-op listener suffices -
    // waitUntilServing()/goto() already surface a spawn failure through their own timeouts.
    proc.on("error", () => { /* no-op by design, per the comment above */ });
    return proc;
}

/** @param {import("node:child_process").ChildProcess} proc */
async function stopTwin(proc) {
    if (proc.exitCode !== null || proc.signalCode !== null) {
        return;
    }
    // SIGINT, not SIGTERM/kill('SIGTERM'): run_generic_integration.py's own graceful-shutdown path
    // (FRAM/SCD30 flush) only runs on KeyboardInterrupt - a plain SIGTERM would skip it, same
    // reasoning as scripts/_digital_twin_ci_suite.py's own _shutdown().
    proc.kill("SIGINT");
    // The SIGKILL fallback timer is cleared once the child is gone. A plain Promise.race leaves
    // the setTimeout pending, and a pending timer keeps Node's event loop alive - which showed up
    // as Vitest's "something prevents Vite server from exiting" on every live-twin run.
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let killTimer;
    try {
        await Promise.race([
            new Promise((resolve) => {
                proc.once("exit", resolve);
            }),
            new Promise((resolve) => {
                killTimer = setTimeout(() => {
                    proc.kill("SIGKILL");
                    resolve(undefined);
                }, SHUTDOWN_TIMEOUT_MS);
            }),
        ]);
    } finally {
        clearTimeout(killTimer);
    }
}

/**
 * The admission ceiling the twin under test was built with, read from the same TOML buildgen reads
 * rather than restated here - so raising a device's own max_connections makes the browser tier
 * open more real tabs instead of leaving it pinned at a number that used to be right.
 * @returns {number}
 */
export function configuredMaxConnections(device = "wozi") {
    const toml = readFileSync(path.join(REPO_ROOT, "devices", `${device}.toml`), "utf8");
    // Deliberately a line match, not a TOML parse: this file has no TOML dependency and the key is
    // a plain top-level int in [device]. A miss throws rather than silently falling back.
    const match = /^max_connections\s*=\s*(?<ceiling>\d+)\s*$/mu.exec(toml);
    if (!match?.groups) {
        throw new Error(`devices/${device}.toml does not state [device].max_connections - the browser tier derives its tab count from it`);
    }
    return Number(match.groups.ceiling);
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
    // to a fixed path by default (run_generic_integration.py exposes no --cfg-path flag).
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
            await livePage.close().catch(() => { /* best-effort teardown - a page already gone is fine */ });
        }
        await stopTwin(proc);
    }
}

/**
 * Parallel real-browser sessions against one live twin - the closest thing this project has to the
 * real multi-client scenario, and the tier that actually exercises a raised connection ceiling in a
 * browser rather than in a socket loop. Every tab loads the real site concurrently; each page load
 * is 2 connections after bundling/inlining (SPECIFICATION.md Part H.7).
 * @param {{context: import("playwright").BrowserContext}} ctx
 * @returns {Promise<{skipped: true, reason: string} | {skipped: false, tabs: number, loaded: number, deviceNames: string[]}>}
 */
export async function runLiveBackendConcurrentTabs({ context }) {
    if (!existsSync(MICROPYTHON_BIN)) {
        return {
            skipped: true,
            reason: `MicroPython Unix port not built at ${MICROPYTHON_BIN} - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)`,
        };
    }
    rmSync(path.join(REPO_ROOT, "digital_twin", "config"), { recursive: true, force: true });

    // Half the ceiling, since each tab costs 2 connections - so the whole admission ceiling is
    // genuinely in use at once rather than a fixed, long-stale 2.
    const tabs = Math.max(2, Math.floor(configuredMaxConnections() / 2));
    const proc = spawnTwin();
    let stderr = "";
    proc.stderr?.on("data", (/** @type {Buffer} */ chunk) => {
        stderr += chunk.toString();
    });

    /** @type {import("playwright").Page[]} */
    const pages = [];
    try {
        await waitUntilServing(READY_TIMEOUT_MS);
        for (let i = 0; i < tabs; i += 1) {
            // eslint-disable-next-line no-await-in-loop -- pages are CREATED sequentially and NAVIGATED together below; that is what makes the loads concurrent rather than the setup
            pages.push(await context.newPage());
        }
        const results = await Promise.all(pages.map(async (page) => {
            await page.goto(`http://${HOST}:${PORT}/`);
            await page.waitForSelector('[data-section-key="system"]', { timeout: 20000 });
            return (await page.locator("#device-name").textContent())?.trim() ?? "";
        }));
        return { skipped: false, tabs, loaded: results.length, deviceNames: results };
    } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        throw new Error(`live-backend concurrent-tab check failed: ${message}\n--- twin stderr ---\n${stderr}`, { cause: err });
    } finally {
        await Promise.all(pages.map((page) => page.close().catch(() => { /* best-effort teardown - a page already gone is fine */ })));
        await stopTwin(proc);
    }
}
