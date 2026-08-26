import js from "@eslint/js";
import globals from "globals";
import html from "eslint-plugin-html";

/**
 * ESLint flat config for js/ and tests_js/ - the JS/HTML/CSS website's ruff-equivalent lint
 * pass (see CLAUDE.md's "Code quality tooling" / SPECIFICATION.md Part H.8). Shipped JS stays plain,
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
        // Standalone Node scripts under scripts/ (e.g. cross_browser_smoke.mjs) - real Node
        // process, same reasoning/globals as the two Vitest command files above. Found unchecked by
        // any configured tool during a pre-merge audit (its own eslint-disable comments implied
        // coverage that didn't actually exist).
        files: ["scripts/**/*.mjs"],
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
