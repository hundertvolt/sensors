// Vitest setup: real timers after every test (spies are restored by restoreMocks in vitest.config.js).
import { afterEach, vi } from "vitest";

afterEach(() => {
    vi.useRealTimers();
});
