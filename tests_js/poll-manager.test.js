import { afterEach, describe, expect, it, vi } from "vitest";
import { pollManager, startPolling } from "../js/poll-manager.js";
import pollManagerSource from "../js/poll-manager.js?raw";
import { readIntConst } from "./_source_constants.js";

// @tunable l0.poll_manager_poll_ms = 20
const STUB_DELAY_MS = 20;

/**
 * A visibility source the test flips by hand. `listenerCount` is what the loop still holds; `fireReleased()`
 * also calls a callback the loop already released, as a change event queued before its stop would.
 * @param {boolean} [startHidden]
 */
function fakeVisibility(startHidden = false) {
    let hidden = startHidden;
    /** @type {Set<() => void>} */
    const listeners = new Set();
    /** @type {(() => void)[]} */
    const everSubscribed = [];
    /** @type {import("../js/poll-manager.js").Visibility} */
    const source = {
        isHidden: () => hidden,
        onChange: (callback) => {
            listeners.add(callback);
            everSubscribed.push(callback);
            return () => {
                listeners.delete(callback);
            };
        },
    };
    return {
        source,
        /** @param {boolean} value */
        setHidden(value) {
            hidden = value;
            for (const callback of [...listeners]) {
                callback();
            }
        },
        fireReleased() {
            for (const callback of everSubscribed) {
                callback();
            }
        },
        get listenerCount() {
            return listeners.size;
        },
    };
}

/**
 * The rejection a promise ends with (the test fails if it resolves instead).
 * @param {Promise<unknown>} promise
 * @returns {Promise<unknown>}
 */
async function rejectionOf(promise) {
    try {
        await promise;
    } catch (error) {
        return error;
    }
    throw new Error("expected the promise to reject, but it resolved");
}

describe("pollManager", () => {
    const originalFetch = window.fetch;

    afterEach(() => {
        window.fetch = originalFetch;
    });

    it("serializes concurrent requests - one in flight at a time", async () => {
        /** @type {number[]} */
        const activeAt = [];
        let concurrentPeak = 0;
        let active = 0;

        window.fetch = vi.fn(async () => {
            active += 1;
            concurrentPeak = Math.max(concurrentPeak, active);
            await new Promise((resolve) => {
                setTimeout(resolve, STUB_DELAY_MS);
            });
            active -= 1;
            activeAt.push(Date.now());
            return new Response(JSON.stringify({ ok: true }), { status: 200 });
        });

        await Promise.all([pollManager.request("/a"), pollManager.request("/b"), pollManager.request("/c")]);

        expect(concurrentPeak).toBe(1);
        expect(window.fetch).toHaveBeenCalledTimes(3);
    });

    it("parses the JSON body and reports ok/status", async () => {
        window.fetch = vi.fn(() => Promise.resolve(new Response(JSON.stringify({ hello: "world" }), { status: 200 })));

        const result = await pollManager.request("/x");

        expect(result.ok).toBe(true);
        expect(result.status).toBe(200);
        expect(result.body).toEqual({ hello: "world" });
    });

    it("rejects with a clear message (and the original SyntaxError as cause) when the body isn't valid JSON", async () => {
        // A genuine transmission error (truncated/corrupted response), not something the server
        // itself would ever intentionally send - see SPECIFICATION.md Part H.4's "PUT/GET error
        // handling" row.
        window.fetch = vi.fn(() => Promise.resolve(new Response("{not valid json", { status: 200 })));

        let caught;
        try {
            await pollManager.request("/torn");
        } catch (error) {
            caught = error;
        }
        expect(caught).toBeInstanceOf(Error);
        expect(/** @type {Error} */ (caught).message).toMatch(/not valid json/i);
        expect(/** @type {Error} */ (caught).cause).toBeInstanceOf(SyntaxError);
    });

    it("answers a non-ok response whose body is not JSON with its status and a null body", async () => {
        // A plain static server's 404 page: the status is the failure the caller reports, not the page's text.
        window.fetch = vi.fn(() => Promise.resolve(new Response("<h1>Not Found</h1>", { status: 404 })));

        await expect(pollManager.request("/missing.json")).resolves.toEqual({ ok: false, status: 404, body: null });
    });

    it("rejects with a clear message when the connection drops mid-stream, while reading the response body", async () => {
        // A response whose underlying stream errors after headers arrive but before the body
        // finishes - a genuine dropped-connection transmission error, not a malformed JSON body.
        const erroringStream = new ReadableStream({
            start(controller) {
                controller.error(new Error("simulated stream failure"));
            },
        });
        window.fetch = vi.fn(() => Promise.resolve(new Response(erroringStream, { status: 200 })));

        let caught;
        try {
            await pollManager.request("/dropped");
        } catch (error) {
            caught = error;
        }
        expect(caught).toBeInstanceOf(Error);
        expect(/** @type {Error} */ (caught).message).toMatch(/interrupted/i);
        expect(/** @type {Error} */ (caught).cause).toBeDefined();
    });

    it("still advances the queue after a torn-JSON failure - the next request isn't stuck behind it", async () => {
        window.fetch = vi
            .fn()
            .mockResolvedValueOnce(new Response("{not valid json", { status: 200 }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));

        await expect(pollManager.request("/torn")).rejects.toThrow(/not valid json/i);
        const second = await pollManager.request("/ok");

        expect(second.body).toEqual({ second: true });
    });

    it("still advances the queue when a request fails", async () => {
        window.fetch = vi
            .fn()
            .mockRejectedValueOnce(new Error("network down"))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));

        await expect(pollManager.request("/fails")).rejects.toThrow("network down");
        const second = await pollManager.request("/ok");

        expect(second.body).toEqual({ second: true });
    });

    it("times out and unblocks the queue when a request hangs forever", async () => {
        vi.useFakeTimers();
        // A real hung connection never resolves at all - the single-flight queue must not wait
        // on it forever (the device has very few available sockets, SPECIFICATION.md Part H.4), so a
        // fetch() that never settles must still eventually be treated as a failure.
        window.fetch = vi
            .fn()
            .mockImplementationOnce(() => new Promise(() => { /* never settles: simulates a hung connection */ }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));

        const hung = pollManager.request("/hangs", undefined, 5000);
        const assertion = expect(hung).rejects.toThrow(/timed out/i);
        await vi.advanceTimersByTimeAsync(5000);
        await assertion;

        vi.useRealTimers();
        const second = await pollManager.request("/ok");
        expect(second.body).toEqual({ second: true });
    });

    it("times out a response whose body never finishes, then runs the next queued request", async () => {
        vi.useFakeTimers();
        // Headers arrive at once; the body never does - the timeout covers the whole request, body read included.
        const stalledBody = new ReadableStream({ start() { /* never enqueues and never closes */ } });
        window.fetch = vi
            .fn()
            .mockResolvedValueOnce(new Response(stalledBody, { status: 200 }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));

        const stalled = pollManager.request("/stalls", undefined, 1000);
        const assertion = expect(stalled).rejects.toThrow("Request to /stalls timed out after 1000ms");
        const next = pollManager.request("/ok");
        await vi.advanceTimersByTimeAsync(1000);
        await assertion;

        expect((await next).body).toEqual({ second: true });
        vi.useRealTimers();
    });

    it("succeeds when the body completes just before the timeout (guard)", async () => {
        vi.useFakeTimers();
        const lateBody = new ReadableStream({
            start(controller) {
                setTimeout(() => {
                    controller.enqueue(new TextEncoder().encode(JSON.stringify({ late: true })));
                    controller.close();
                }, 999);
            },
        });
        window.fetch = vi.fn(() => Promise.resolve(new Response(lateBody, { status: 200 })));

        const late = pollManager.request("/late", undefined, 1000);
        await vi.advanceTimersByTimeAsync(999);

        await expect(late).resolves.toEqual({ ok: true, status: 200, body: { late: true } });
        vi.useRealTimers();
    });

    it("aborts the underlying fetch's signal when a request times out", async () => {
        vi.useFakeTimers();
        /** @type {AbortSignal | undefined} */
        let capturedSignal;
        window.fetch = vi.fn((_url, init) => {
            capturedSignal = /** @type {RequestInit} */ (init).signal ?? undefined;
            return new Promise(() => { /* never settles: simulates a hung connection */ });
        });

        const hung = pollManager.request("/hangs", undefined, 1000);
        const assertion = expect(hung).rejects.toThrow(/timed out/i);
        await vi.advanceTimersByTimeAsync(1000);
        await assertion;

        expect(capturedSignal?.aborted).toBe(true);
        vi.useRealTimers();
    });

    it("rejects a queued request whose signal aborts before its turn with AbortError, never fetching it", async () => {
        /** @type {() => void} */
        let releaseFirst = () => { /* replaced once the first fetch is in flight */ };
        window.fetch = vi.fn(
            () =>
                new Promise((resolve) => {
                    releaseFirst = () => resolve(new Response(JSON.stringify({ first: true }), { status: 200 }));
                }),
        );
        const first = pollManager.request("/first");
        const controller = new AbortController();
        const queued = pollManager.request("/queued", undefined, undefined, controller.signal);
        await vi.waitFor(() => expect(window.fetch).toHaveBeenCalledTimes(1));

        controller.abort();
        releaseFirst();

        expect((await first).body).toEqual({ first: true });
        const error = await rejectionOf(queued);
        expect(error).toBeInstanceOf(DOMException);
        expect(/** @type {DOMException} */ (error).name).toBe("AbortError");
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });

    it("rejects an in-flight request with AbortError when its signal aborts, and the queue advances", async () => {
        window.fetch = vi
            .fn()
            .mockImplementationOnce(() => new Promise(() => { /* never settles and ignores its signal */ }))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));
        const controller = new AbortController();
        const inFlight = pollManager.request("/hangs", undefined, undefined, controller.signal);
        const next = pollManager.request("/ok");
        await vi.waitFor(() => expect(window.fetch).toHaveBeenCalledTimes(1));

        controller.abort();

        expect(/** @type {DOMException} */ (await rejectionOf(inFlight)).name).toBe("AbortError");
        expect((await next).body).toEqual({ second: true });
    });

    it("drops a queued request when its queue signal aborts, while one already in flight runs to its end", async () => {
        /** @type {() => void} */
        let releaseFirst = () => { /* replaced once the first fetch is in flight */ };
        /** @type {AbortSignal | undefined} */
        let firstSignal;
        window.fetch = vi
            .fn()
            .mockImplementationOnce((_url, init) => {
                firstSignal = /** @type {RequestInit} */ (init).signal ?? undefined;
                return new Promise((resolve) => {
                    releaseFirst = () => resolve(new Response(JSON.stringify({ first: true }), { status: 200 }));
                });
            })
            .mockResolvedValue(new Response(JSON.stringify({ queued: true }), { status: 200 }));
        const queue = new AbortController();
        const first = pollManager.request("/first", undefined, undefined, undefined, queue.signal);
        const queued = pollManager.request("/queued", undefined, undefined, undefined, queue.signal);
        await vi.waitFor(() => expect(window.fetch).toHaveBeenCalledTimes(1));

        queue.abort();
        releaseFirst();

        expect((await first).body).toEqual({ first: true });
        expect(firstSignal?.aborted).toBe(false);
        expect(/** @type {DOMException} */ (await rejectionOf(queued)).name).toBe("AbortError");
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });
});

describe("startPolling", () => {
    it("waits for one poll to resolve before scheduling the next", async () => {
        vi.useFakeTimers();
        let callCount = 0;
        /** @type {(value?: unknown) => void} */
        let resolveCurrent = () => { /* replaced below, by the first poll's own resolver */ };

        const stop = startPolling(async () => {
            callCount += 1;
            await new Promise((resolve) => {
                resolveCurrent = resolve;
            });
        }, 10);

        await vi.advanceTimersByTimeAsync(0);
        expect(callCount).toBe(1);

        await vi.advanceTimersByTimeAsync(1000);
        expect(callCount).toBe(1); // still awaiting the first call - no overlap

        resolveCurrent();
        await vi.advanceTimersByTimeAsync(10);
        expect(callCount).toBe(2);

        stop();
        resolveCurrent();
        await vi.advanceTimersByTimeAsync(1000);
        expect(callCount).toBe(2); // stopped - no further polls

        vi.useRealTimers();
    });

    it("reports each failure through onError and keeps polling at the doubled interval", async () => {
        vi.useFakeTimers();
        const consoleError = vi.spyOn(console, "error");
        const onError = vi.fn();
        /** @type {number[]} */
        const calledAt = [];

        const stop = startPolling(
            () => {
                calledAt.push(Date.now());
                return Promise.reject(new Error("boom"));
            },
            10,
            { onError },
        );

        await vi.advanceTimersByTimeAsync(0);
        expect(onError).toHaveBeenCalledTimes(1);
        expect(onError).toHaveBeenLastCalledWith(expect.objectContaining({ message: "boom" }));
        await vi.advanceTimersByTimeAsync(10 + 20 + 40);

        expect(calledAt.slice(1).map((at, index) => at - /** @type {number} */ (calledAt[index]))).toEqual([10, 20, 40]);
        expect(onError).toHaveBeenCalledTimes(4);
        expect(consoleError).not.toHaveBeenCalled(); // the caller's onError is the one failure path

        stop();
        consoleError.mockRestore();
        vi.useRealTimers();
    });

    it("backs off 3000, 6000, 12000 ... capped at POLL_BACKOFF_MAX_MS while failing, and returns to 3000 after one success", async () => {
        const cap = readIntConst(pollManagerSource, "POLL_BACKOFF_MAX_MS");
        vi.useFakeTimers();
        let failing = true;
        /** @type {number[]} */
        const calledAt = [];
        const stop = startPolling(
            () => {
                calledAt.push(Date.now());
                return failing ? Promise.reject(new Error("device down")) : Promise.resolve();
            },
            3000,
            { onError: () => { /* the gaps below are the observation */ } },
        );
        const failingGaps = [3000, 6000, 12000, 24000, 48000, 96000, 192000].map((ms) => Math.min(ms, cap));

        await vi.advanceTimersByTimeAsync(failingGaps.reduce((sum, ms) => sum + ms, 0));
        failing = false;
        await vi.advanceTimersByTimeAsync(cap + 3000);

        const gaps = calledAt.slice(1).map((at, index) => at - /** @type {number} */ (calledAt[index]));
        expect(gaps).toEqual([...failingGaps, cap, 3000]);
        stop();
        vi.useRealTimers();
    });

    it("ends the loop after the first success when stopAfterSuccess is set, releasing the visibility listener", async () => {
        vi.useFakeTimers();
        const visibility = fakeVisibility();
        let callCount = 0;
        startPolling(
            () => {
                callCount += 1;
                return callCount < 3 ? Promise.reject(new Error("not yet")) : Promise.resolve();
            },
            10,
            { visibility: visibility.source, onError: () => { /* two failures before the success */ }, stopAfterSuccess: true },
        );

        await vi.advanceTimersByTimeAsync(10 + 20);
        expect(callCount).toBe(3);
        await vi.advanceTimersByTimeAsync(1000);
        expect(callCount).toBe(3);
        expect(visibility.listenerCount).toBe(0);
        vi.useRealTimers();
    });

    it("schedules nothing after a stop() that lands while a poll is in flight (guard)", async () => {
        vi.useFakeTimers();
        let callCount = 0;
        /** @type {() => void} */
        let resolveCurrent = () => { /* replaced by the poll in flight */ };
        const stop = startPolling(() => {
            callCount += 1;
            return new Promise((resolve) => {
                resolveCurrent = () => resolve();
            });
        }, 10);
        await vi.advanceTimersByTimeAsync(0);

        stop();
        resolveCurrent();
        await vi.advanceTimersByTimeAsync(20);

        expect(callCount).toBe(1);
        vi.useRealTimers();
    });

    it("pauses while the page is hidden, ticks once on becoming visible, and releases its listener on stop", async () => {
        vi.useFakeTimers();
        const visibility = fakeVisibility();
        let callCount = 0;
        const stop = startPolling(
            () => {
                callCount += 1;
                return Promise.resolve();
            },
            10,
            { visibility: visibility.source },
        );
        await vi.advanceTimersByTimeAsync(0);
        expect(callCount).toBe(1);

        visibility.setHidden(true);
        await vi.advanceTimersByTimeAsync(100);
        expect(callCount).toBe(1);

        visibility.setHidden(false);
        await vi.advanceTimersByTimeAsync(0);
        expect(callCount).toBe(2);
        await vi.advanceTimersByTimeAsync(10);
        expect(callCount).toBe(3);

        expect(visibility.listenerCount).toBe(1);
        stop();
        expect(visibility.listenerCount).toBe(0);
        vi.useRealTimers();
    });

    it("runs nothing while the page starts hidden, and ticks once it becomes visible", async () => {
        vi.useFakeTimers();
        const visibility = fakeVisibility(true);
        let callCount = 0;
        const stop = startPolling(
            () => {
                callCount += 1;
                return Promise.resolve();
            },
            10,
            { visibility: visibility.source },
        );
        await vi.advanceTimersByTimeAsync(100);
        expect(callCount).toBe(0);

        visibility.setHidden(false);
        await vi.advanceTimersByTimeAsync(0);
        expect(callCount).toBe(1);
        stop();
        vi.useRealTimers();
    });

    it("runs no tick for a visibility change that arrives after stop() (guard)", async () => {
        vi.useFakeTimers();
        const visibility = fakeVisibility();
        let callCount = 0;
        const stop = startPolling(
            () => {
                callCount += 1;
                return Promise.resolve();
            },
            10,
            { visibility: visibility.source },
        );
        await vi.advanceTimersByTimeAsync(0);
        visibility.setHidden(true);
        stop();

        visibility.setHidden(false);
        visibility.fireReleased();
        await vi.advanceTimersByTimeAsync(100);

        expect(callCount).toBe(1);
        vi.useRealTimers();
    });
});
