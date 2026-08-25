import js from "@eslint/js";
import globals from "globals";

/**
 * ESLint flat config for js/ and tests_js/ - the JS/HTML/CSS website's ruff-equivalent lint
 * pass (see CLAUDE.md's "Code quality tooling" / WEBSITE_PLAN.md §6). Shipped JS stays plain,
 * hand-written ES modules; this is dev-tooling only, mirroring pyproject.toml's [tool.ruff] role.
 */
// Beyond eslint:recommended: core rules that catch real bugs (accidental narrowing, race-prone
// async patterns, ...), not style - the JS-side equivalent of pyproject.toml's stricter-than-
// default ruff selection (CLAUDE.md's "Code quality tooling"). Verified current/non-deprecated
// directly against the installed `eslint` package's own rule metadata (10.8.1), not assumed.
const BUG_CATCHING_RULES = {
    "array-callback-return": "error",
    "no-await-in-loop": "error",
    "no-constructor-return": "error",
    "no-duplicate-imports": "error",
    "no-promise-executor-return": "error",
    "no-self-compare": "error",
    "no-template-curly-in-string": "error",
    "no-unmodified-loop-condition": "error",
    "no-unreachable-loop": "error",
    "no-use-before-define": ["error", { functions: false }],
    "require-atomic-updates": "error",
};

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
        rules: BUG_CATCHING_RULES,
    },
    {
        files: ["tests_js/**/*.js"],
        ignores: ["tests_js/_live_twin_command.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
        rules: BUG_CATCHING_RULES,
    },
    {
        // Vitest Commands API implementations run server-side, in the real Node process - not the
        // sandboxed browser context every other tests_js/*.js file runs in (WEBSITE_PLAN.md §10
        // item 5's own rationale for needing this file at all). Node globals, not browser ones.
        files: ["tests_js/_live_twin_command.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        rules: BUG_CATCHING_RULES,
    },
];
