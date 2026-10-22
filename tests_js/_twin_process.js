// The launch frame the live command modules and the smoke share (SPECIFICATION.md Part H.7): the Unix-port probe, the
// twin layout, one device's twin on a given port with its own site, readiness, shutdown, the captive-DNS port lock each
// twin holds while it runs, and the verdict read from a stopped twin's output.

import { execFileSync, spawn } from "node:child_process";
import { mkdtempSync, readFileSync, realpathSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { LAYOUT_FILE, twinLayout, withSite } from "./_micropypath.js";
import { acquirePortLock } from "./_port_lock.js";
import { twinStartFailure } from "./_twin_start_failure.js";

export const HOST = "127.0.0.1";
// @tunable l0.live_twin_ready_timeout_ms = 20000
export const READY_TIMEOUT_MS = 20000;
// @tunable l0.live_twin_shutdown_timeout_ms = 15000
export const SHUTDOWN_TIMEOUT_MS = 15000;
const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// The twin layout of the one MICROPYPATH definition, read once.
export const MICROPYPATH = twinLayout(readFileSync(path.join(REPO_ROOT, LAYOUT_FILE), "utf8"), LAYOUT_FILE);
const MISSING_INTERPRETER = "MicroPython Unix port not built - run 'uv run toolchain/setup_toolchain.py setup' first (CI's web-unit-tests job does this automatically)";
/** @type {string | undefined} the standard binary the probe named, once asked */
let interpreter;
// Every twin's captive DNS binds this product-fixed port, so a twin runs only while its runner holds the port's lock.
const DNS_PORT = 53;
const LOCK_RUNNER = "the vitest live tier";
const CONFIG_DIR_PREFIX = path.join(tmpdir(), "sensors-live-");
const RUNNER = "digital_twin/run_generic_integration.py";
// Past this many bytes the Unix port cannot intern a string as a qstr and dies before the runner starts: scripts/
// _twin_process.py's _QSTR_MAX_BYTES, read against the interpreter there and pinned to this copy by a tests_scripts test.
const QSTR_MAX_BYTES = 255;
/** @type {WeakMap<import("node:child_process").ChildProcess, Error>} */
const spawnErrors = new WeakMap();
/** @type {WeakMap<import("node:child_process").ChildProcess, () => void>} */
const lockReleases = new WeakMap();

/**
 * `start()`'s process, or the lock released again when it throws, so a failed launch leaves no port held.
 * @param {() => void} release
 * @param {() => import("node:child_process").ChildProcess} start
 * @returns {import("node:child_process").ChildProcess}
 */
function spawnOrRelease(release, start) {
    try {
        return start();
    } catch (err) {
        release();
        throw err;
    }
}

/**
 * Stops one twin: SIGINT, then SIGKILL past the shutdown bound, returning only once it has exited.
 * @param {import("node:child_process").ChildProcess} proc
 */
async function stopProcess(proc) {
    if (proc.pid === undefined || proc.exitCode !== null || proc.signalCode !== null) {
        return; // never started (waitUntilServing() names its spawn error) or already gone
    }
    const exited = new Promise((resolve) => {
        proc.once("exit", resolve);
    });
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
            exited,
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
    await exited; // a killed twin still holds the port until it has exited, and the next check needs it free
}

/**
 * Each string the interpreter would intern before the runner starts and cannot, named with its size in bytes: the
 * arguments from the runner on, the runner's real directory, every MICROPYPATH entry but a ~/ one it builds from $HOME.
 * @param {string[]} args
 * @param {NodeJS.ProcessEnv} env
 * @returns {string[]}
 */
function uninternable(args, env) {
    /** @type {[string, string][]} */
    const named = args.map((value, i) => {
        const before = args[i - 1] ?? "";
        return [before.startsWith("--") && !value.startsWith("--") ? `${before}'s value` : `argument ${i}`, value];
    });
    named.push(["the runner's directory", path.dirname(realpathSync(path.join(REPO_ROOT, RUNNER)))]);
    (env.MICROPYPATH ?? "").split(":").forEach((entry, i) => {
        if (!entry.startsWith("~/") || env.HOME === undefined) {
            named.push([`MICROPYPATH entry ${i + 1}`, entry]);
        }
    });
    return named.flatMap(([name, value]) => {
        const size = Buffer.byteLength(value, "utf8");
        return size > QSTR_MAX_BYTES ? [`${name} (${size} bytes)`] : [];
    });
}

/**
 * Holds the captive-DNS port for one stretch that boots twins more than once (a restart): twins the stretch spawns
 * take it again within this process, so another runner cannot take it between them.
 * @returns {() => void} the release
 */
export function holdTwinPorts() {
    return acquirePortLock(DNS_PORT, LOCK_RUNNER);
}

/**
 * The standard Unix-port binary, as scripts/_unix_port.sh's check names it (asked once, building nothing), or an error
 * carrying the probe's own words: the live tier needs the binary, and a run without it fails, never skips.
 * @returns {string}
 */
export function requireInterpreter() {
    if (interpreter === undefined) {
        try {
            interpreter = execFileSync("bash", ["scripts/_unix_port.sh", "check", "standard"], { cwd: REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
        } catch (err) {
            const said = /** @type {{stderr?: unknown}} */ (err).stderr;
            throw new Error(`${MISSING_INTERPRETER} (the probe said: ${typeof said === "string" ? said.trim() : String(err)})`, { cause: err });
        }
    }
    return interpreter;
}

/**
 * A fresh config directory for one command's twins: its own, under the OS temp directory, never the manual run's
 * digital_twin/config/, which no command touches.
 * @returns {string}
 */
export function makeConfigDir() {
    return mkdtempSync(CONFIG_DIR_PREFIX);
}

/**
 * Removes a directory makeConfigDir() made, and refuses any other.
 * @param {string} dir
 */
export function removeConfigDir(dir) {
    if (!path.resolve(dir).startsWith(CONFIG_DIR_PREFIX)) {
        throw new Error(`refusing to remove ${dir}: not a config directory makeConfigDir() made`);
    }
    rmSync(dir, { recursive: true, force: true });
}

/** @param {number} ms */
export function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

/**
 * Boots `device`'s twin on `port` under the captive-DNS lock: build/generated_src first, sensortask_<device>.py's one
 * home (SPECIFICATION.md Part L.2), its own site (build/generated_html/<device>, package.json's "pretest" hooks), the
 * caller's config directory (makeConfigDir()), the rest in memory; an uninternable string throws before any of it.
 * @param {{device: string, port: number, configDir: string}} twin
 * @returns {import("node:child_process").ChildProcess}
 */
export function spawnTwin({ device, port, configDir }) {
    const args = [
        RUNNER,
        "--module",
        `sensortask_${device}`,
        "--wiring-plan",
        path.join(REPO_ROOT, "build", "generated_src", `sensortask_${device}_wiring_plan.json`),
        "--device",
        device,
        "--host",
        HOST,
        "--port",
        String(port),
        "--fram-state-path",
        "", // in-memory only - see digital_twin/README.md's "FRAM persistence" section for this convention
        "--scd30-state-path",
        "", // same convention, "SCD30 persistence" section
        "--mem-backup-state-path",
        "", // the watchdog scratch registers, likewise
        "--config-dir",
        configDir,
    ];
    // The device's own built site in place of the unit tier's shared copy, so a twin never serves another device's site.
    const env = { ...process.env, MICROPYPATH: withSite(MICROPYPATH, `build/generated_html/${device}`), TZ: "UTC" };
    const refused = uninternable(args, env);
    if (refused.length > 0) {
        throw new Error(`the twin was not started: ${refused.join(", ")} - the Unix port interns each as a qstr of at most ${QSTR_MAX_BYTES} bytes and dies before the runner starts`);
    }
    const bin = requireInterpreter();
    const release = acquirePortLock(DNS_PORT, LOCK_RUNNER);
    const proc = spawnOrRelease(release, () => spawn(bin, args, {
        cwd: REPO_ROOT,
        env,
        // Both streams are drained: an undrained pipe blocks the child; the drained text is scanned for the memory markers.
        stdio: ["ignore", "pipe", "pipe"],
    }));
    lockReleases.set(proc, release);
    // An unhandled ChildProcess 'error' event crashes the whole Node/Vitest process, skipping the
    // caller's try/finally: the listener keeps the error for waitUntilServing() to name.
    proc.on("error", (err) => { spawnErrors.set(proc, err); });
    return proc;
}

/**
 * Stops a twin and, once it has exited, releases the captive-DNS lock its spawn took.
 * @param {import("node:child_process").ChildProcess} proc
 */
export async function stopTwin(proc) {
    try {
        await stopProcess(proc);
    } finally {
        lockReleases.get(proc)?.();
        lockReleases.delete(proc);
    }
}

/**
 * The verdict once a command's twins have stopped: an allocation-failure marker or a restart sign anywhere in a
 * twin's output fails it (SPECIFICATION.md Part I.4(e)), quoting the lines, even when the check itself passed.
 * @param {string} what the command, for the message
 * @param {ReturnType<typeof import("./_memory_markers.js").drainChildOutput>[]} outputs every twin it started, in order
 * @param {unknown} failure what the check itself threw, or null
 * @param {boolean} drained whether every output stream closed, so the scans saw everything
 */
export function twinVerdict(what, outputs, failure, drained) {
    const marked = outputs.flatMap((output) => output.markerLines());
    const reset = outputs.flatMap((output) => output.resetLines());
    const checkFailed = failure === null ? "" : `\n(the check itself also failed: ${failure instanceof Error ? failure.message : String(failure)})`;
    const cause = failure === null ? undefined : { cause: failure };
    if (marked.length > 0) {
        throw new Error(`${what}: the twin logged an allocation failure:\n${marked.join("\n")}${checkFailed}`, cause);
    }
    if (reset.length > 0) {
        throw new Error(`${what}: the twin reset itself, so the page talked to a device that was not running:\n${reset.join("\n")}${checkFailed}`, cause);
    }
    if (!drained) {
        throw new Error(`${what}: the twin's output did not close within ${SHUTDOWN_TIMEOUT_MS}ms of it stopping, so the allocation-failure scan is incomplete${checkFailed}`, cause);
    }
    if (failure !== null) {
        const message = failure instanceof Error ? failure.message : String(failure);
        throw new Error(`${what} failed: ${message}\n--- twin output ---\n${outputs.map((output) => output.text()).join("--- restarted twin ---\n")}`, cause);
    }
}

/**
 * Waits until the twin answers on `port`, naming a spawn error or an early exit at once rather than waiting it out.
 * @param {import("node:child_process").ChildProcess} proc
 * @param {number} port
 * @param {number} timeoutMs
 */
export async function waitUntilServing(proc, port, timeoutMs) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
        const failure = twinStartFailure({ spawnError: spawnErrors.get(proc) ?? null, exitCode: proc.exitCode, signalCode: proc.signalCode });
        if (failure !== null) {
            throw new Error(failure);
        }
        try {
            // eslint-disable-next-line no-await-in-loop -- sequential polling: each probe waits for the one before
            const res = await fetch(`http://${HOST}:${port}/`);
            if (res.status === 200) {
                return;
            }
        } catch {
            // Not up yet - keep polling.
        }
        // eslint-disable-next-line no-await-in-loop -- same reasoning as above
        await sleep(250);
    }
    throw new Error(`digital twin never started serving on ${HOST}:${port} within ${timeoutMs}ms`);
}
