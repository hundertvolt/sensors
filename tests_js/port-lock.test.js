// tests_js/_port_lock.js holds a product-fixed port for one runner at a time under scripts/_port_lock.sh's contract:
// the same directory, files, message and inherited owner chain, so either language's holder refuses the other's taker.
// Each case runs real node and bash processes over a private lock root (the probePortLock command).
import { commands } from "vitest/browser";
import { describe, expect, it } from "vitest";

/** @typedef {import("vitest/browser").BrowserCommands["probePortLock"]} Probe */
/** @typedef {Parameters<Probe>[0]["taker"]} Actor */
/** @typedef {Actor["lang"]} Lang */

/**
 * @param {"node" | "bash"} lang
 * @param {number} port
 * @param {string} runner
 * @param {Partial<Actor>} [more]
 * @returns {Actor}
 */
function actor(lang, port, runner, more = {}) {
    return { lang, port, runner, ...more };
}

/**
 * @param {string} runner
 * @param {number | null} pid
 * @returns {string}
 */
function heldBy(runner, pid) {
    return `port 53 is held by ${runner} (pid ${pid}) - run the suites one after the other (CLAUDE.md)`;
}

describe("the JS port lock", () => {
    it.each(/** @type {[Lang, Lang][]} */ ([["node", "node"], ["node", "bash"], ["bash", "node"], ["bash", "bash"]]))("a live %s holder refuses a %s taker, naming the holder the same way", async (holder, taker) => {
        const probe = await commands.probePortLock({ holder: actor(holder, 53, `holder-${holder}`), taker: actor(taker, 53, `taker-${taker}`) });
        expect([probe.code, probe.stderr.trim()]).toEqual([1, heldBy(`holder-${holder}`, probe.holderPid)]);
        expect(probe.lock).toEqual({ runner: `holder-${holder}\n`, pid: `${probe.holderPid}\n` });
    });

    it("refuses a taker whose inherited chain lists the port but not the holder's pid", async () => {
        const probe = await commands.probePortLock({ holder: actor("node", 53, "holder"), taker: actor("node", 53, "stranger"), inherit: { owner: "1", held: "53" } });
        expect([probe.code, probe.stderr.trim()]).toEqual([1, heldBy("holder", probe.holderPid)]);
    });

    it("appends the port and its own pid to an inherited chain, once each, and releases the lock when its process exits", async () => {
        const probe = await commands.probePortLock({ taker: actor("node", 53, "fresh"), inherit: { owner: "1", held: "123" } });
        expect(probe.code).toBe(0);
        expect(probe.stdout).toMatch(/^took (?<pid>\d+) held=123 53 owner=1 \k<pid>$/mu);
        expect(probe.rootAfterTaker).toEqual([]);
    });

    it.each(/** @type {[Lang, Lang, Lang][]} */ ([["node", "bash", "node"], ["bash", "node", "bash"]]))("lets a %s holder's child (%s, taking another port) and grandchild (%s) pass on the held port", async (first, second, third) => {
        const probe = await commands.probePortLock({ taker: actor(first, 53, "holder", { then: actor(second, 123, "child", { then: actor(third, 53, "grandchild") }) }) });
        expect([probe.code, probe.stderr]).toEqual([0, ""]);
        expect(probe.stdout.match(/^then 0$/gmu)).toHaveLength(2);
        expect(probe.rootAfterTaker).toEqual([]);
    });

    it("refuses the holder's own descendant once its inherited chain no longer lists the port", async () => {
        const probe = await commands.probePortLock({ taker: actor("node", 53, "holder", { then: actor("node", 53, "child", { dropHeld: true }) }) });
        const holderPid = Number(/^took (?<pid>\d+)/mu.exec(probe.stdout)?.groups?.pid);
        expect([probe.code, probe.stderr.trim()]).toEqual([1, heldBy("holder", holderPid)]);
    });

    it("is re-entrant in one process: an inner release keeps the lock, the outer one removes it", async () => {
        const probe = await commands.probePortLock({ taker: actor("node", 53, "twice", { twice: true }) });
        expect(probe.code).toBe(0);
        expect(probe.stdout).toContain("after inner true after outer false");
    });

    it.each(/** @type {[string, "dead" | ""][]} */ ([["a dead pid", "dead"], ["no pid at all", ""]]))("takes over a lock recording %s, leaving nothing behind", async (_case, pid) => {
        const probe = await commands.probePortLock({ taker: actor("node", 53, "successor"), plant: { port: 53, pid, runner: "gone" } });
        expect([probe.code, probe.stderr]).toEqual([0, ""]);
        expect(probe.stdout).toMatch(/^took \d+ /mu);
        expect(probe.rootAfterTaker).toEqual([]);
    });

    it.each([[0, "runner"], [65536, "runner"], [53, ""]])("refuses port %j with runner %j as a usage error", async (port, runner) => {
        const probe = await commands.probePortLock({ taker: actor("node", port, runner) });
        expect(probe.code).toBe(1);
        expect(probe.stderr).toContain("needs a port 1-65535 and a runner name");
    });
});
