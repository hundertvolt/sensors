// Tests tests_js/_expected_display.js against hand-written texts, never against js/field-format.js: it is the live
// tier's independent oracle for what the page shows.
import { describe, expect, it } from "vitest";
import { expectedDisplay } from "./_expected_display.js";

describe("expectedDisplay", () => {
    it("shows a missing value as a dash", () => {
        expect(expectedDisplay({ kind: "number" }, null)).toBe("—");
        expect(expectedDisplay({ kind: "string" }, undefined)).toBe("—");
    });

    it("shows a masked field as eight dots, whatever it holds", () => {
        expect(expectedDisplay({ kind: "string", mask: true }, "hunter2")).toBe("••••••••");
    });

    it("shows an enum by its option label, an unknown value as itself", () => {
        const field = { kind: "enum", options: [{ value: 1, label: "Low" }, { value: 2, label: "High" }] };
        expect(expectedDisplay(field, 2)).toBe("High");
        expect(expectedDisplay(field, 7)).toBe("7");
    });

    it("pads and rounds a number to its decimals by integer arithmetic, sign kept", () => {
        expect(expectedDisplay({ kind: "number", decimals: 3 }, 1.5)).toBe("1.500");
        expect(expectedDisplay({ kind: "number", decimals: 3 }, -0.0005)).toBe("-0.001");
        expect(expectedDisplay({ kind: "number", decimals: 0 }, 412.6)).toBe("413");
        expect(expectedDisplay({ kind: "number", decimals: 2 }, 25)).toBe("25.00");
    });

    it("gives a fraction with no decimals of its own the site's default, a whole number none", () => {
        expect(expectedDisplay({ kind: "number" }, 5.25, 2)).toBe("5.25");
        expect(expectedDisplay({ kind: "number" }, 0.1000000015, 2)).toBe("0.10");
        expect(expectedDisplay({ kind: "number" }, 10, 2)).toBe("10");
        expect(expectedDisplay({ kind: "number" }, 5.25)).toBe("5.25");
    });

    it("shows anything else as its plain text", () => {
        expect(expectedDisplay({ kind: "string" }, "pool.ntp.org")).toBe("pool.ntp.org");
        expect(expectedDisplay({ kind: "number" }, 1800)).toBe("1800");
    });
});
