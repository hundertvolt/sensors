import { afterEach, describe, expect, it, vi } from "vitest";
import { pollManager, startPolling } from "../js/poll-manager.js";

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
                setTimeout(resolve, 20);
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
        window.fetch = vi.fn(async () => new Response(JSON.stringify({ hello: "world" }), { status: 200 }));

        const result = await pollManager.request("/x");

        expect(result.ok).toBe(true);
        expect(result.status).toBe(200);
        expect(result.body).toEqual({ hello: "world" });
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
        // on it forever (the device has very few available sockets, WEBSITE_PLAN.md §4), so a
        // fetch() that never settles must still eventually be treated as a failure.
        window.fetch = vi
            .fn()
            .mockImplementationOnce(() => new Promise(() => {}))
            .mockResolvedValueOnce(new Response(JSON.stringify({ second: true }), { status: 200 }));

        const hung = pollManager.request("/hangs", undefined, 5000);
        const assertion = expect(hung).rejects.toThrow(/timed out/i);
        await vi.advanceTimersByTimeAsync(5000);
        await assertion;

        vi.useRealTimers();
        const second = await pollManager.request("/ok");
        expect(second.body).toEqual({ second: true });
    });

    it("isBusy reflects whether a request is currently in flight", async () => {
        /** @type {(value?: unknown) => void} */
        let resolveFetch = () => {};
        window.fetch = vi.fn(
            () =>
                new Promise((resolve) => {
                    resolveFetch = () => resolve(new Response(JSON.stringify({}), { status: 200 }));
                }),
        );

        expect(pollManager.isBusy).toBe(false);
        const pending = pollManager.request("/x");
        await vi.waitFor(() => expect(pollManager.isBusy).toBe(true));

        resolveFetch();
        await pending;
        expect(pollManager.isBusy).toBe(false);
    });

    it("aborts the underlying fetch's signal when a request times out", async () => {
        vi.useFakeTimers();
        /** @type {AbortSignal | undefined} */
        let capturedSignal;
        window.fetch = vi.fn((_url, init) => {
            capturedSignal = /** @type {RequestInit} */ (init).signal ?? undefined;
            return new Promise(() => {});
        });

        const hung = pollManager.request("/hangs", undefined, 1000);
        const assertion = expect(hung).rejects.toThrow(/timed out/i);
        await vi.advanceTimersByTimeAsync(1000);
        await assertion;

        expect(capturedSignal?.aborted).toBe(true);
        vi.useRealTimers();
    });
});

describe("startPolling", () => {
    it("waits for one poll to resolve before scheduling the next", async () => {
        vi.useFakeTimers();
        let callCount = 0;
        /** @type {(value?: unknown) => void} */
        let resolveCurrent = () => {};

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

    it("logs and keeps polling when pollOnce rejects, instead of stopping the loop", async () => {
        vi.useFakeTimers();
        const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
        let callCount = 0;

        const stop = startPolling(async () => {
            callCount += 1;
            throw new Error("boom");
        }, 10);

        await vi.advanceTimersByTimeAsync(0);
        expect(callCount).toBe(1);
        expect(consoleError).toHaveBeenCalledWith("Poll failed:", expect.any(Error));

        await vi.advanceTimersByTimeAsync(10);
        expect(callCount).toBe(2); // one failed poll doesn't stop the loop

        stop();
        consoleError.mockRestore();
        vi.useRealTimers();
    });
});
