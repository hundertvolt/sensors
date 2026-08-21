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
            await new Promise((resolve) => setTimeout(resolve, 20));
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
});
