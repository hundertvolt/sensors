// Types for the custom Vitest browser commands vitest.config.js registers from the Node-context tests_js command
// modules: Vitest's own form is a `declare module` block, which a plain runtime-executed .js file cannot hold, hence
// this type-only sidecar for live-backend*.test.js and the other callers.
//
// Written out, not `typeof` imports: each implementation takes Vitest's injected `ctx` first, which callers never pass,
// and an import would pull Node's ambient types into the browser-context program (tsconfig.json's "exclude"). Each
// return type is kept in sync by hand with its command's own @returns JSDoc.
//
// Required, not decorative: without a top-level import/export of its own TS reads this file as an ambient script, and
// the `declare module` block then replaces the real "vitest/browser" module (its `commands` export vanished when this
// line was removed) instead of augmenting it.
export {};

/** One process taking a port lock: in node through tests_js/_port_lock.js or in bash through scripts/_port_lock.sh. */
type PortLockActor = { lang: "node" | "bash"; port: number; runner: string; twice?: boolean; dropHeld?: boolean; then?: PortLockActor };

declare module "vitest/browser" {
    interface BrowserCommands {
        runLiveBackendSmoke: (device: string, testTimeoutMs: number) => Promise<{
            titleHasSensorStation: boolean;
            deviceName: string;
            firstStatus: string | null;
            resubmitStatus: string | null;
        }>;
        runLiveBackendConcurrentTabs: (device: string, testTimeoutMs: number) => Promise<{ tabs: number; loadedFirstPass: number; loadedAfterRetry: number; failures: string[] }>;
        runLiveBackendRestartRecovery: (device: string, testTimeoutMs: number) => Promise<{ bannerShown: boolean; recovered: boolean; reloaded: boolean }>;
        getLiveMatrixConfig: () => Promise<{ shard: string }>;
        startLiveMatrix: (device: string) => Promise<void>;
        stopLiveMatrix: () => Promise<void>;
        getRealCurrentValues: (paths: string[]) => Promise<Record<string, unknown>>;
        applyField: (args: {
            sectionKey: string;
            groupKey: string;
            fieldKey: string;
            field: import("../js/definitions.js").FieldDef;
            value: unknown;
            expectRenderedValue: unknown;
            defaultDecimals?: number | undefined;
            confirmMessage?: string;
            readCaption?: boolean;
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
            valueText: string | null;
            errcountRows: string[];
        }>;
        archiveErrcount: (label: string) => Promise<string>;
        probeLintRule: (args: { rule: string; value: number }) => Promise<number>;
        probePortLock: (args: {
            holder?: PortLockActor;
            taker: PortLockActor;
            inherit?: { owner: string; held: string };
            plant?: { port: number; pid: "dead" | ""; runner: string };
        }) => Promise<{
            holderPid: number | null;
            code: number | null;
            stdout: string;
            stderr: string;
            lock: { runner: string | null; pid: string | null } | null;
            rootAfterTaker: string[];
        }>;
    }
}

