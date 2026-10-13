// Counts the connections one page load opens, by their first request: the document and its assets are the page's own
// (SPECIFICATION.md H.7), any other path is a data request, and a connection still empty once the page's first data
// request went out is a browser's spare socket, counted on its own because it still holds a device slot.

import net from "node:net";

/** @param {string} line a connection's first request line @returns {boolean} whether it asks for data, not the page */
export function isDataRequest(line) {
    const path = (line.split(" ")[1] ?? "").split("?")[0] ?? "";
    return path !== "/" && !/\.[A-Za-z0-9]+$/.test(path);
}

/**
 * @param {(string | null)[]} firstRequests each connection's first request line, or null when it sent none
 * @returns {{page: number, speculative: number, data: number}}
 */
export function classifyConnections(firstRequests) {
    let page = 0;
    let speculative = 0;
    let data = 0;
    for (const line of firstRequests) {
        if (line === null) {
            speculative += 1;
        } else if (isDataRequest(line)) {
            data += 1;
        } else {
            page += 1;
        }
    }
    return { page, speculative, data };
}

/** @typedef {{reset: () => void, firstRequests: () => (string | null)[], firstDataRequest: (waitMs: number) => Promise<boolean>, port: () => number, close: () => Promise<void>}} CountingProxy */

/**
 * A TCP proxy in front of a server that records every connection a browser opens through it, with its first request line.
 * @param {string} host @param {number} listenPort 0 for any free port @param {number} upstreamPort @returns {Promise<CountingProxy>}
 */
export function startCountingProxy(host, listenPort, upstreamPort) {
    /** @type {(string | null)[]} */
    let firstRequests = [];
    let dataSeen = false;
    /** @typedef {{done: (seen: boolean) => void, timer?: ReturnType<typeof setTimeout>}} Waiter */
    /** @type {Waiter[]} */
    let waiters = [];
    const release = (/** @type {Waiter} */ waiter, /** @type {boolean} */ seen) => {
        clearTimeout(waiter.timer);
        waiters = waiters.filter((w) => w !== waiter);
        waiter.done(seen);
    };
    const settle = (/** @type {boolean} */ seen) => {
        for (const waiter of [...waiters]) {
            release(waiter, seen);
        }
    };
    /** @type {Set<net.Socket>} */
    const sockets = new Set();
    const server = net.createServer((client) => {
        // The load's own list, so a previous load's socket writing late never lands in the next one.
        const records = firstRequests;
        const slot = records.length;
        records.push(null);
        client.once("data", (chunk) => {
            const [line] = chunk.toString("latin1").split("\r\n", 1);
            records[slot] = line ?? "";
            if (records === firstRequests && isDataRequest(records[slot])) {
                dataSeen = true;
                settle(true);
            }
        });
        const upstream = net.connect(upstreamPort, host);
        const close = () => {
            client.destroy();
            upstream.destroy();
            sockets.delete(client);
            sockets.delete(upstream);
        };
        sockets.add(client);
        sockets.add(upstream);
        for (const socket of [client, upstream]) {
            socket.on("error", close);
            socket.on("close", close);
        }
        client.pipe(upstream);
        upstream.pipe(client);
    });
    return new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(listenPort, host, () => {
            resolve({
                reset: () => {
                    firstRequests = [];
                    dataSeen = false;
                    settle(false);
                },
                firstRequests: () => [...firstRequests],
                firstDataRequest: (waitMs) => new Promise((done) => {
                    if (dataSeen) {
                        done(true);
                        return;
                    }
                    /** @type {Waiter} */
                    const waiter = { done };
                    waiter.timer = setTimeout(() => release(waiter, false), waitMs);
                    waiters.push(waiter);
                }),
                port: () => /** @type {net.AddressInfo} */ (server.address()).port,
                close: () => new Promise((done) => {
                    settle(false);
                    for (const socket of sockets) {
                        socket.destroy();
                    }
                    server.close(() => done());
                }),
            });
        });
    });
}

/**
 * The first request of each connection open when a navigation finished, read once the page's first data request has
 * reached the proxy or waitMs passed: a socket the page opened for that request but had not yet written then counts as data.
 * @param {CountingProxy} proxy @param {number} waitMs @returns {Promise<(string | null)[]>}
 */
export async function settledPageLoadConnections(proxy, waitMs) {
    const opened = proxy.firstRequests().length;
    await proxy.firstDataRequest(waitMs);
    return proxy.firstRequests().slice(0, opened);
}
