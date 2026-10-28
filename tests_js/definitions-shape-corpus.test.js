// Runs js/definitions.js's validator over tests_scripts/definitions_shape_cases.json, the corpus
// tests_scripts' Python shape check reads too, so the two agree.
import { expect, it } from "vitest";
import cases from "../tests_scripts/definitions_shape_cases.json";
import { validateDefinitions } from "../js/definitions.js";

it.each(cases)("$name", ({ definitions, valid }) => {
    expect(validateDefinitions(definitions).length === 0).toBe(valid);
});
