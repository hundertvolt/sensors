import js from "@eslint/js";
import globals from "globals";
import html from "eslint-plugin-html";

/**
 * ESLint flat config for js/ and tests_js/ - the JS/HTML/CSS website's ruff-equivalent lint
 * pass (see CLAUDE.md's "Code quality tooling" / SPECIFICATION.md Part H.8). Shipped JS stays plain,
 * hand-written ES modules; this is dev-tooling only, mirroring pyproject.toml's [tool.ruff] role.
 */
// Beyond eslint:recommended. The JS-side counterpart of pyproject.toml's `select = ["ALL"]`:
// ESLint has no "all rules" switch that is safe to use (its own docs advise against `eslint:all`,
// which enables mutually contradictory stylistic rules), so this is the curated equivalent -
// every core rule that catches a real defect or enforces a decision, with pure style-preference
// bans (no-bitwise, no-plusplus, one-var, func-style, id-length, sort-keys, no-ternary,
// no-magic-numbers, no-undefined, no-continue) deliberately left out: they fight this codebase's
// hand-chosen style without catching anything. Verified rule-by-rule against the installed
// eslint (10.8.1). Almost all of these already reported zero findings, so this mostly locks in
// discipline the codebase already had; the handful that did fire were fixed in js//tests_js/
// rather than switched off.
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
    // js/poll-manager.js's "Poll failed:" is the poll loop's ONLY failure diagnostic and is
    // directly asserted by tests_js/poll-manager.test.js; tests_js/live-backend.test.js's skip
    // warning is the documented reason that check skipped itself. Banning those would delete
    // real signal, so the ban is scoped to console.log and friends rather than all of console.
    // (scripts/*.mjs is a CLI tool where console IS the output - overridden in its own block below)
    "no-console": ["error", { allow: ["error", "warn"] }],

    // --- complexity ceilings, pinned at this codebase's CURRENT measured maximum so they gate
    // REGRESSION rather than demand a rewrite of already-working code. Mirrors pyproject.toml's
    // [tool.ruff.lint.mccabe]/[tool.ruff.lint.pylint] policy exactly. Ratchet DOWNWARD as the
    // offenders (js/mock-server.js's route dispatcher at 41, js/definitions.js's
    // validateDefinitions at 37) are genuinely simplified; never upward for new code.
    complexity: ["error", 41],
    "max-depth": ["error", 4],
    "max-nested-callbacks": ["error", 4],
    "max-classes-per-file": ["error", 2],
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
        ignores: ["tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js"],
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
        // sandboxed browser context every other tests_js/*.js file runs in (SPECIFICATION.md Part
        // H.7's own rationale for needing this file at all). Node globals, not browser ones.
        files: ["tests_js/_live_twin_command.js", "tests_js/_live_matrix_command.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        rules: BUG_CATCHING_RULES,
    },
    {
        // This repo's own root-level tooling config. Without this block they match no `files`
        // entry and so get only js.configs.recommended, not BUG_CATCHING_RULES - the linter would
        // be holding its own config to a weaker standard than the code it lints. Node globals:
        // both are loaded by the Node process, never shipped to a browser.
        files: ["eslint.config.js", "vitest.config.js"],
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.node,
            },
        },
        rules: BUG_CATCHING_RULES,
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
        rules: { ...BUG_CATCHING_RULES, "no-console": "off" },
    },
    {
        // html/index.html's <script type="module"> bootstrap can't be extracted into its own
        // js/ file: scripts/build_website.sh relies on that <script> importing the literal path
        // "../js/app.js", which stays identical between `npm run preview` (the real, separate
        // js/app.js prototype entry point) and a real device build (where js/app.js is the staged
        // bundle) - extracting it would either break that path identity or require a build-time
        // text rewrite the script deliberately avoids (see build_website.sh's own header comment).
        // eslint-plugin-html instead lints the inline script in place, exactly like any other
        // module script, without moving it out of the HTML file.
        files: ["html/**/*.html"],
        plugins: { html },
        languageOptions: {
            ecmaVersion: "latest",
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
        rules: BUG_CATCHING_RULES,
    },
];
