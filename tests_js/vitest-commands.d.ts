// Ambient module augmentation for the custom Vitest browser command registered in
// vitest.config.js (`test.browser.commands.runLiveBackendSmoke`, implemented in
// tests_js/_live_twin_command.js) - the shape Vitest's own docs use for this is a `declare module`
// block, which isn't valid syntax in a plain, runtime-executed .js file, hence this type-only
// sidecar. See tests_js/live-backend.test.js for the one caller.
//
// Deliberately NOT `import type { runLiveBackendSmoke } from "./_live_twin_command.js"` + `typeof`:
// that file's own real signature takes the Vitest-injected `ctx` as its first parameter (see its
// own JSDoc), which callers never pass themselves (Vitest's RPC layer supplies it server-side) -
// using `typeof` here would describe the wrong (implementation-side) arity, and would also pull
// that Node-context file into this browser-context program's dependency graph, leaking its
// `node:*`/`process`/`Buffer` ambient types into every other tests_js/*.js file's own type-check
// (tsconfig.json's own "exclude" comment explains why that file needs a separate program at all).
// This return type is kept in sync by hand with that file's own `@returns` JSDoc - two small,
// co-located declarations, not worth a shared import at the cost of either problem above.
//
// The `export {}` below is required, not decorative: without at least one top-level import/export
// of its own, TS treats this file as an ambient *script*, and the `declare module` block inside it
// then *replaces* the real "vitest/browser" module wholesale (confirmed directly - removing this
// line makes the real module's own `commands` export vanish) rather than *augmenting* it, which is
// the whole point here.
export {};

declare module "vitest/browser" {
    interface BrowserCommands {
        runLiveBackendSmoke: () => Promise<
            | { skipped: true; reason: string }
            | { skipped: false; titleHasSensorStation: boolean; deviceName: string; debugLevelApplyStatus: string | null }
        >;
    }
}
