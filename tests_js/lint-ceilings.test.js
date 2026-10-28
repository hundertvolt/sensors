// ESLint's four complexity ceilings sit at the measured maximum and only go down: each reports at
// least one finding one below its configured value and none at it (SPECIFICATION.md D.10, H.8). The
// ruff half: tests_scripts/test_lint_ceilings.py.
/// <reference types="vite/client" />
import { commands } from "vitest/browser";
import { describe, expect, test } from "vitest";
import configText from "../eslint.config.js?raw";

const CEILINGS = ["complexity", "max-depth", "max-nested-callbacks", "max-classes-per-file"];

/** @param {string} rule */
function configuredValue(rule) {
    const key = rule.includes("-") ? `"${rule}"` : rule;
    const match = configText.match(new RegExp(`${key}: \\["error", (\\d+)\\]`, "u"));
    if (match === null || match[1] === undefined) {
        throw new Error(`eslint.config.js sets no "error" ceiling for ${rule}`);
    }
    return Number(match[1]);
}

describe("ESLint complexity ceilings", () => {
    for (const rule of CEILINGS) {
        test(
            `${rule} sits at its measured maximum`,
            async () => {
                const value = configuredValue(rule);
                expect(await commands.probeLintRule({ rule, value })).toBe(0);
                // max-classes-per-file accepts no value below 1, so its floor cannot be probed lower.
                if (rule !== "max-classes-per-file" || value > 1) {
                    expect(await commands.probeLintRule({ rule, value: value - 1 })).toBeGreaterThan(0);
                }
            },
            60000, // two full-tree ESLint runs in the Node process
        );
    }
});
