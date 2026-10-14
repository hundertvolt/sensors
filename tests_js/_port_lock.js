// Node side of scripts/_port_lock.sh: one runner per product-fixed port at a time, the holder's own process and its
// descendants pass, a dead holder's lock is taken over - the same lock directory, files, message and owner chain.
// probePortLock() is the Commands API probe behind tests_js/port-lock.test.js; no runner calls it.

import { spawn, spawnSync } from "node:child_process";
import { accessSync, constants, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, renameSync, rmdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ATTEMPTS = 10;
// A holder writes its pid right after its mkdir: a lock without one is waited for this long before it reads as dead.
const PID_WAITS = 20;
const PID_WAIT_MS = 50;
const PROBE_WAIT_MS = 10000;
const SLEEPER = new Int32Array(new SharedArrayBuffer(4));
/** @type {Map<string, number>} each lock this process took, by directory, with its count of unreleased takes */
const holds = new Map();
let exitHookArmed = false;

// The probe's two actors: take one port, print what the lock and the chain say, then hold, run a child actor, or exit;
// a node actor with dropHeld first forgets the ports its chain lists.
const NODE_ACTOR = `
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
const { acquirePortLock } = await import(process.env.LOCK_MODULE_URL);
const spec = JSON.parse(process.env.LOCK_ACTOR);
if (spec.dropHeld) {
    delete process.env.SENSORS_PORT_LOCKS_HELD;
}
const dir = path.join(process.env.XDG_RUNTIME_DIR, "sensors-port-" + spec.port + ".lock");
try {
    const release = acquirePortLock(spec.port, spec.runner);
    console.log("took " + process.pid + " held=" + process.env.SENSORS_PORT_LOCKS_HELD + " owner=" + process.env.SENSORS_PORT_LOCK_OWNER);
    if (spec.twice) {
        acquirePortLock(spec.port, spec.runner)();
        const afterInner = existsSync(dir);
        release();
        console.log("after inner " + afterInner + " after outer " + existsSync(dir));
    }
    if (spec.then) {
        const then = spec.then;
        const env = { ...process.env, LOCK_ACTOR: JSON.stringify(then), LOCK_PORT: String(then.port), LOCK_RUNNER: then.runner, LOCK_THEN: then.then ? JSON.stringify(then.then) : "", LOCK_HOLD: "" };
        const child = then.lang === "bash"
            ? spawnSync("bash", ["-c", process.env.LOCK_BASH_SRC], { env, stdio: "inherit" })
            : spawnSync(process.execPath, ["--input-type=module", "-e", process.env.LOCK_NODE_SRC], { env, stdio: "inherit" });
        console.log("then " + child.status);
        process.exitCode = child.status ?? 1;
    }
    if (spec.hold) {
        setInterval(() => {}, 1000);
    }
} catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exitCode = 1;
}
`;
const BASH_ACTOR = `
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take "$LOCK_PORT" "$LOCK_RUNNER"
echo "took $$ held=$SENSORS_PORT_LOCKS_HELD owner=$SENSORS_PORT_LOCK_OWNER"
if [ -n "\${LOCK_THEN:-}" ]; then
    LOCK_ACTOR="$LOCK_THEN" LOCK_THEN="" node --input-type=module -e "$LOCK_NODE_SRC"
    rc=$?
    echo "then $rc"
    exit "$rc"
fi
if [ -n "\${LOCK_HOLD:-}" ]; then
    while :; do sleep 0.1; done
fi
`;

/**
 * Whether `pid` names a live process; kill(pid, 0) fails with EPERM on another user's, which /proc still shows.
 * @param {string} pid
 * @returns {boolean}
 */
function isAlive(pid) {
    if (!/^[1-9][0-9]*$/u.test(pid)) {
        return false;
    }
    try {
        process.kill(Number(pid), 0);
        return true;
    } catch {
        return existsSync(`/proc/${pid}`);
    }
}

/**
 * @param {string} item
 * @param {string | undefined} list a space-separated list, as the chain variables hold them
 * @returns {boolean}
 */
function isListed(item, list) {
    return (list ?? "").split(" ").includes(item);
}

/**
 * The environment one probe actor starts with: a private lock root, the two actor sources, and either no chain or
 * the one given, so a holder of the outer run can never let an actor pass.
 * @param {string} root
 * @param {{owner: string, held: string} | undefined} inherit
 * @returns {NodeJS.ProcessEnv}
 */
function actorEnv(root, inherit) {
    /** @type {NodeJS.ProcessEnv} */
    const env = { ...process.env };
    delete env.SENSORS_PORT_LOCK_OWNER;
    delete env.SENSORS_PORT_LOCKS_HELD;
    return {
        ...env,
        ...(inherit === undefined ? {} : { SENSORS_PORT_LOCK_OWNER: inherit.owner, SENSORS_PORT_LOCKS_HELD: inherit.held }),
        XDG_RUNTIME_DIR: root,
        PATH: `${path.dirname(process.execPath)}:${process.env.PATH ?? ""}`,
        LOCK_MODULE_URL: pathToFileURL(fileURLToPath(import.meta.url)).href,
        LOCK_NODE_SRC: NODE_ACTOR,
        LOCK_BASH_SRC: BASH_ACTOR,
    };
}

/**
 * Only the taker whose mkdir of <lock>/takeover succeeds moves a dead holder's lock away, and only once its pid is
 * still dead after the wait; the rename makes the lock vanish at once rather than file by file.
 * @param {string} dir
 */
function clearStale(dir) {
    try {
        mkdirSync(path.join(dir, "takeover"));
    } catch {
        sleepMs(PID_WAIT_MS);
        return;
    }
    if (isAlive(pidOf(dir))) {
        try {
            rmdirSync(path.join(dir, "takeover"));
        } catch {
            // Gone with its lock already: nothing left to back off from.
        }
        return;
    }
    const stale = `${dir}.stale.${process.pid}`;
    try {
        renameSync(dir, stale);
    } catch {
        return; // another taker moved it first
    }
    rmSync(stale, { recursive: true, force: true });
}

/**
 * The pid a lock records, waited for while its holder may still be writing it; "" for none.
 * @param {string} dir
 * @returns {string}
 */
function pidOf(dir) {
    for (let tries = 0; ; tries += 1) {
        const pid = readText(path.join(dir, "pid")) ?? "";
        if (/^[1-9][0-9]*$/u.test(pid) || !existsSync(dir) || tries >= PID_WAITS) {
            return pid;
        }
        sleepMs(PID_WAIT_MS);
    }
}

/**
 * A plant for the probe: a lock left by a holder that died, recording a dead pid or none.
 * @param {string} root
 * @param {{port: number, pid: "dead" | "", runner: string}} plant
 */
function plantLock(root, plant) {
    const dir = path.join(root, `sensors-port-${plant.port}.lock`);
    mkdirSync(dir);
    writeFileSync(path.join(dir, "runner"), `${plant.runner}\n`);
    writeFileSync(path.join(dir, "pid"), plant.pid === "dead" ? `${spawnSync("true").pid}\n` : "");
}

/**
 * A file's exact text, or null when it cannot be read.
 * @param {string} file
 * @returns {string | null}
 */
function readRaw(file) {
    try {
        return readFileSync(file, "utf8");
    } catch {
        return null;
    }
}

/**
 * A file's text without its trailing newlines, as bash's $(cat) reads it, or null when it cannot be read.
 * @param {string} file
 * @returns {string | null}
 */
function readText(file) {
    try {
        return readFileSync(file, "utf8").replace(/\n+$/u, "");
    } catch {
        return null;
    }
}

/**
 * Removes one lock this process holds once its last take is released; the rename makes it vanish at once.
 * @param {string} dir
 */
function release(dir) {
    const count = holds.get(dir) ?? 0;
    if (count > 1) {
        holds.set(dir, count - 1);
        return;
    }
    holds.delete(dir);
    if (readText(path.join(dir, "pid")) !== String(process.pid)) {
        return; // never this process's, or already taken over
    }
    const released = `${dir}.released.${process.pid}`;
    try {
        renameSync(dir, released);
    } catch {
        return;
    }
    rmSync(released, { recursive: true, force: true });
}

/**
 * Collects an actor's output until it exits, killing its group past the probe's bound.
 * @param {import("node:child_process").ChildProcess} proc
 * @param {(stdout: string) => boolean} [enough] resolves early, the actor still running, once its output satisfies it
 * @returns {Promise<{code: number | null, stdout: string, stderr: string}>}
 */
function settle(proc, enough) {
    return new Promise((resolve) => {
        const out = { stdout: "", stderr: "" };
        const finish = () => resolve({ code: proc.exitCode, ...out });
        const timer = setTimeout(() => {
            stopGroup(proc);
            out.stderr += `\nthe actor did not settle within ${PROBE_WAIT_MS}ms`;
            finish();
        }, PROBE_WAIT_MS);
        proc.stdout?.on("data", (chunk) => {
            out.stdout += String(chunk);
            if (enough?.(out.stdout)) {
                clearTimeout(timer);
                finish();
            }
        });
        proc.stderr?.on("data", (chunk) => {
            out.stderr += String(chunk);
        });
        proc.once("close", () => {
            clearTimeout(timer);
            finish();
        });
    });
}

/**
 * Blocks for `ms`: the lock is taken synchronously, as bash's sleep would, and only while a holder writes its pid.
 * @param {number} ms
 */
function sleepMs(ms) {
    Atomics.wait(SLEEPER, 0, 0, ms);
}

/**
 * Starts one probe actor in its own process group, so stopping it also stops whatever it started.
 * @param {{lang: "node" | "bash", port: number, runner: string, twice?: boolean, dropHeld?: boolean, then?: object}} spec
 * @param {NodeJS.ProcessEnv} env
 * @param {boolean} hold
 * @returns {import("node:child_process").ChildProcess}
 */
function startActor(spec, env, hold) {
    const own = { ...spec, hold };
    const actorEnvironment = { ...env, LOCK_ACTOR: JSON.stringify(own), LOCK_PORT: String(spec.port), LOCK_RUNNER: spec.runner, LOCK_THEN: spec.then ? JSON.stringify(spec.then) : "", LOCK_HOLD: hold ? "1" : "" };
    const [command, args] = spec.lang === "bash" ? ["bash", ["-c", BASH_ACTOR]] : [process.execPath, ["--input-type=module", "-e", NODE_ACTOR]];
    return spawn(command, args, { cwd: REPO_ROOT, env: actorEnvironment, detached: true, stdio: ["ignore", "pipe", "pipe"] });
}

/**
 * Stops a probe actor's whole process group.
 * @param {import("node:child_process").ChildProcess} proc
 */
function stopGroup(proc) {
    if (proc.pid !== undefined && proc.exitCode === null && proc.signalCode === null) {
        try {
            process.kill(-proc.pid, "SIGTERM");
        } catch {
            // Already gone.
        }
    }
}

/**
 * Holds `port` for `runner` until the returned release (or this process's exit), or throws naming the live holder.
 * Its own process and any process whose inherited chain lists the holder and the port pass without taking it.
 * @param {number} port
 * @param {string} runner
 * @returns {() => void} the release: a no-op for a lock this process did not take
 */
export function acquirePortLock(port, runner) {
    if (!Number.isInteger(port) || port < 1 || port > 65535 || runner === "") {
        throw new Error(`acquirePortLock(port, runner) needs a port 1-65535 and a runner name, not ${JSON.stringify(port)} ${JSON.stringify(runner)}`);
    }
    const root = process.env.XDG_RUNTIME_DIR || "/tmp";
    try {
        accessSync(root, constants.W_OK);
        if (!statSync(root).isDirectory()) {
            throw new Error("not a directory");
        }
    } catch {
        throw new Error(`acquirePortLock: the lock root ${root} is not a writable directory`);
    }
    const dir = path.join(root, `sensors-port-${port}.lock`);
    const own = String(process.pid);
    for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
        try {
            mkdirSync(dir);
        } catch {
            const pid = pidOf(dir);
            if (isAlive(pid)) {
                if (pid === own) {
                    holds.set(dir, (holds.get(dir) ?? 0) + 1);
                    return () => release(dir);
                }
                if (isListed(pid, process.env.SENSORS_PORT_LOCK_OWNER) && isListed(String(port), process.env.SENSORS_PORT_LOCKS_HELD)) {
                    return () => { /* the ancestor that took it releases it */ };
                }
                throw new Error(`port ${port} is held by ${readText(path.join(dir, "runner")) ?? "an unnamed runner"} (pid ${pid}) - run the suites one after the other (CLAUDE.md)`);
            }
            if (existsSync(dir)) {
                clearStale(dir);
            }
            continue;
        }
        try {
            writeFileSync(path.join(dir, "runner"), `${runner}\n`);
            writeFileSync(path.join(dir, "pid"), `${own}\n`);
        } catch {
            continue; // the lock moved away while it was written: take it again
        }
        if (readText(path.join(dir, "pid")) !== own) {
            continue;
        }
        process.env.SENSORS_PORT_LOCKS_HELD = isListed(String(port), process.env.SENSORS_PORT_LOCKS_HELD) ? process.env.SENSORS_PORT_LOCKS_HELD : [process.env.SENSORS_PORT_LOCKS_HELD, port].filter(Boolean).join(" ");
        process.env.SENSORS_PORT_LOCK_OWNER = isListed(own, process.env.SENSORS_PORT_LOCK_OWNER) ? process.env.SENSORS_PORT_LOCK_OWNER : [process.env.SENSORS_PORT_LOCK_OWNER, own].filter(Boolean).join(" ");
        holds.set(dir, 1);
        if (!exitHookArmed) {
            exitHookArmed = true;
            process.on("exit", () => {
                for (const held of [...holds.keys()]) {
                    holds.set(held, 1);
                    release(held);
                }
            });
        }
        return () => release(dir);
    }
    throw new Error(`port ${port}: its lock ${dir} could not be taken in ${ATTEMPTS} attempts - if no runner holds the port, remove that directory`);
}

/**
 * The Commands API probe: on a private lock root, optionally plants a dead holder's lock or starts a live holder,
 * runs the taker to its end, and reports its exit, output, the lock it left and the root's entries afterwards.
 * @param {unknown} _context Vitest's injected command context (unused)
 * @param {{holder?: Parameters<typeof startActor>[0], taker: Parameters<typeof startActor>[0], inherit?: {owner: string, held: string}, plant?: {port: number, pid: "dead" | "", runner: string}}} args
 * @returns {Promise<{holderPid: number | null, code: number | null, stdout: string, stderr: string, lock: {runner: string | null, pid: string | null} | null, rootAfterTaker: string[]}>}
 */
export async function probePortLock(_context, { holder, taker, inherit, plant }) {
    const root = mkdtempSync(path.join(tmpdir(), "sensors-port-lock-"));
    /** @type {import("node:child_process").ChildProcess | undefined} */
    let held;
    try {
        if (plant !== undefined) {
            plantLock(root, plant);
        }
        let holderPid = null;
        if (holder !== undefined) {
            held = startActor(holder, actorEnv(root, undefined), true);
            const started = await settle(held, (stdout) => /^took \d+/mu.test(stdout));
            holderPid = Number(/^took (?<pid>\d+)/mu.exec(started.stdout)?.groups?.pid ?? Number.NaN);
            if (!Number.isInteger(holderPid)) {
                throw new Error(`the ${holder.lang} holder never took its lock: ${started.stderr}`);
            }
        }
        const ran = await settle(startActor(taker, actorEnv(root, inherit), false));
        const dir = path.join(root, `sensors-port-${taker.port}.lock`);
        const lock = existsSync(dir) ? { runner: readRaw(path.join(dir, "runner")), pid: readRaw(path.join(dir, "pid")) } : null;
        return { holderPid, ...ran, lock, rootAfterTaker: readdirSync(root).sort() };
    } finally {
        if (held !== undefined) {
            stopGroup(held);
            await settle(held);
        }
        rmSync(root, { recursive: true, force: true });
    }
}
