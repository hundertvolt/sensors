import comments from "@eslint-community/eslint-plugin-eslint-comments";
import js from "@eslint/js";
import globals from "globals";
import html from "eslint-plugin-html";

/**
 * ESLint flat config for js/ and tests_js/ - the JS/HTML/CSS website's ruff-equivalent lint
 * pass (see CLAUDE.md's "Code quality tooling" / SPECIFICATION.md Part H.8). Shipped JS stays plain,
 * hand-written ES modules; this is dev-tooling only, mirroring pyproject.toml's [tool.ruff] role.
 */
// Beyond eslint:recommended: the curated counterpart of ruff's select = ["ALL"] - every core rule
// that catches a real defect or enforces a decision, style-preference bans left out
// (SPECIFICATION.md H.8).
const BUG_CATCHING_RULES = {
    // --- correctness / likely bugs ---
    "array-callback-return": "error",
    "consistent-return": "error",
    "no-async-promise-executor": "error",
    "no-await-in-loop": "error",
    "no-constructor-return": "error",
    "no-duplicate-imports": "error",
    "no-invalid-this": "error",
    "no-loop-func": "error",
    "no-promise-executor-return": "error",
    "no-self-compare": "error",
    "no-template-curly-in-string": "error",
    "no-unmodified-loop-condition": "error",
    "no-unreachable-loop": "error",
    "no-unused-private-class-members": "error",
    "no-use-before-define": ["error", { functions: false }],
    "require-atomic-updates": "error",
    "require-await": "error",

    // --- unsafe constructs ---
    "no-caller": "error",
    "no-div-regex": "error",
    "no-extend-native": "error",
    "no-implied-eval": "error",
    "no-iterator": "error",
    "no-new-func": "error",
    "no-new-wrappers": "error",
    "no-octal-escape": "error",
    "no-proto": "error",
    "no-script-url": "error",

    // --- error handling ---
    "no-throw-literal": "error",
    "prefer-promise-reject-errors": "error",

    // --- scope / shadowing / implicit globals ---
    "no-implicit-globals": "error",
    "no-label-var": "error",
    "no-labels": "error",
    "no-lone-blocks": "error",
    "no-shadow": "error",
    "no-undef-init": "error",
    "no-var": "error",

    // --- comparison / coercion ---
    eqeqeq: "error",
    "no-eq-null": "error",
    "no-implicit-coercion": "error",
    radix: "error",
    yoda: "error",

    // --- clarity, each one a decision rather than a preference ---
    curly: "error",
    "default-case-last": "error",
    "dot-notation": "error",
    "grouped-accessor-pairs": "error",
    "guard-for-in": "error",
    "no-else-return": "error",
    "no-empty-function": "error",
    "no-lonely-if": "error",
    "no-multi-assign": "error",
    "no-negated-condition": "error",
    "no-nested-ternary": "error",
    "no-new": "error",
    "no-object-constructor": "error",
    "no-param-reassign": "error",
    "no-return-assign": "error",
    "no-sequences": "error",
    "no-useless-call": "error",
    "no-useless-computed-key": "error",
    "no-useless-concat": "error",
    "no-useless-rename": "error",
    "no-void": "error",
    "symbol-description": "error",
    "unicode-bom": "error",

    // --- modern-syntax preferences the whole codebase already follows ---
    "accessor-pairs": "error",
    camelcase: "error",
    "class-methods-use-this": "error",
    "logical-assignment-operators": "error",
    "object-shorthand": "error",
    "operator-assignment": "error",
    "prefer-arrow-callback": "error",
    "prefer-const": "error",
    "prefer-destructuring": "error",
    "prefer-exponentiation-operator": "error",
    "prefer-named-capture-group": "error",
    "prefer-numeric-literals": "error",
    "prefer-object-spread": "error",
    "prefer-regex-literals": "error",
    "prefer-spread": "error",
    "prefer-template": "error",

    // --- console.log is debug residue; console.error/warn are real diagnostics ---
    // a section's once-per-episode failure line (js/render.js) is real signal; scripts/*.mjs is exempt below (H.8).
    "no-console": ["error", { allow: ["error", "warn"] }],

    // --- complexity ceilings at the measured maximum, so they gate regression: ratchet DOWN only, pinned by
    // tests_js/lint-ceilings.test.js (H.8) ---
    complexity: ["error", 22],
    "max-depth": ["error", 4],
    "max-nested-callbacks": ["error", 4],
    "max-classes-per-file": ["error", 1],
};

// The shipped page inserts every server- or user-supplied string as text, never as markup (SPECIFICATION.md H.4).
const PRODUCTION_ONLY_RULES = {
    "no-restricted-properties": [
        "error",
        { property: "innerHTML" },
        { property: "outerHTML" },
        { property: "insertAdjacentHTML" },
        { object: "document", property: "write" },
        { object: "document", property: "writeln" },
    ],
};

// Every disable comment names its rule and a reason after " -- ", and none switches off every rule (SPECIFICATION.md H.8).
const COMMENT_RULES = {
    "@eslint-community/eslint-comments/require-description": ["error", { ignore: [] }],
    "@eslint-community/eslint-comments/no-unlimited-disable": "error",
};
const COMMENT_PLUGIN = { "@eslint-community/eslint-comments": comments };

// Node-context tests_js files (Vitest Commands API modules and their Node-only helpers, the summary reporter) run in the
// real Node process, not the browser every other tests_js/*.js file runs in (SPECIFICATION.md H.7).
const NODE_CONTEXT_TEST_FILES = ["tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js", "tests_js/_lint_command.js", "tests_js/_summary_reporter.js", "tests_js/_port_lock.js", "tests_js/_twin_process.js"];

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
        plugins: COMMENT_PLUGIN,
        rules: { ...BUG_CATCHING_RULES, ...PRODUCTION_ONLY_RULES, ...COMMENT_RULES },
    },
    {
        files: ["tests_js/**/*.js"],
        ignores: NODE_CONTEXT_TEST_FILES,
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
        plugins: COMMENT_PLUGIN,
        rules: { ...BUG_CATCHING_RULES, ...COMMENT_RULES },
    },
    {
        // Node globals, not browser ones: see NODE_CONTEXT_TEST_FILES.
        files: NODE_CONTEXT_TEST_FILES,
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        plugins: COMMENT_PLUGIN,
        rules: { ...BUG_CATCHING_RULES, ...COMMENT_RULES },
    },
    {
        // The repo's own root-level configs, held to the same rules as the code they lint; Node
        // globals, since both run in Node, never in a browser.
        files: ["eslint.config.js", "vitest.config.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        plugins: COMMENT_PLUGIN,
        rules: { ...BUG_CATCHING_RULES, ...COMMENT_RULES },
    },
    {
        // Standalone Node scripts under scripts/ (e.g. cross_browser_smoke.mjs) - real Node
        // process, same reasoning/globals as the two Vitest command files above.
        files: ["scripts/**/*.mjs"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        // console IS this file's output channel - it is a standalone CLI smoke-check runner, not
        // browser code, so its progress/result reporting is the point rather than debug residue.
        plugins: COMMENT_PLUGIN,
        rules: { ...BUG_CATCHING_RULES, ...COMMENT_RULES, "no-console": "off" },
    },
    {
        // html/index.html's inline module bootstrap stays inline - scripts/_stage_website.py checks its
        // literal "../js/app.js" import (H.8) - so eslint-plugin-html lints it in place.
        files: ["html/**/*.html"],
        plugins: { html, ...COMMENT_PLUGIN },
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
        rules: { ...BUG_CATCHING_RULES, ...PRODUCTION_ONLY_RULES, ...COMMENT_RULES },
    },
];
