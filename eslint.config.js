import js from "@eslint/js";
import globals from "globals";

/**
 * ESLint flat config for js/ and tests_js/ - the JS/HTML/CSS website's ruff-equivalent lint
 * pass (see CLAUDE.md's "Code quality tooling" / WEBSITE_PLAN.md §6). Shipped JS stays plain,
 * hand-written ES modules; this is dev-tooling only, mirroring pyproject.toml's [tool.ruff] role.
 */
export default [
    js.configs.recommended,
    {
        files: ["js/**/*.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
    },
    {
        files: ["tests_js/**/*.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
    },
];
