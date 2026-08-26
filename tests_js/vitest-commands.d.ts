// Ambient module augmentation for the custom Vitest browser commands registered in
// vitest.config.js (`test.browser.commands`, implemented in tests_js/_live_twin_command.js and
// tests_js/_live_matrix_command.js) - the shape Vitest's own docs use for this is a `declare
// module` block, which isn't valid syntax in a plain, runtime-executed .js file, hence this
// type-only sidecar. See tests_js/live-backend.test.js and tests_js/live-backend-put-matrix.test.js
// for the callers.
//
// Deliberately NOT `import type {...} from "./_live_twin_command.js"` (or the matrix file) +
// `typeof`: each file's own real signature takes the Vitest-injected `ctx` as its first parameter
// (see each file's own JSDoc) on the functions that need it, which callers never pass themselves
// (Vitest's RPC layer supplies it server-side) - using `typeof` here would describe the wrong
// (implementation-side) arity, and would also pull those Node-context files into this
// browser-context program's dependency graph, leaking their `node:*`/`process`/`Buffer` ambient
// types into every other tests_js/*.js file's own type-check (tsconfig.json's own "exclude"
// comment explains why those files need a separate program at all). These return types are kept in
// sync by hand with each file's own `@returns` JSDoc - small, co-located declarations, not worth a
// shared import at the cost of either problem above.
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
        startLiveMatrix: () => Promise<{ skipped: true; reason: string } | { skipped: false }>;
        stopLiveMatrix: () => Promise<void>;
        getRealCurrentValues: (paths: string[]) => Promise<Record<string, unknown>>;
        applyField: (args: {
            sectionKey: string;
            groupKey: string;
            fieldKey: string;
            field: import("../js/definitions.js").FieldDef;
            value: unknown;
            expectRenderedValue: unknown;
        }) => Promise<{
            applyStatus: string;
            captionText: string | null;
            toggleValue: string | null;
            selectValue: string | null;
        }>;
        applyUnchangedFieldExpectNothingToSubmit: (args: {
            sectionKey: string;
            groupKey: string;
            fieldKey: string;
            kind: "toggle" | "enum";
            value: unknown;
        }) => Promise<{ resultText: string | null; applyStatus: string | null }>;
        remountAndReadField: (args: { sectionKey: string; groupKey: string; fieldKey: string; kind: string }) => Promise<{
            placeholder: string | null;
            toggleValue: string | null;
            toggleText: string | null;
            selectValue: string | null;
        }>;
    }
}
