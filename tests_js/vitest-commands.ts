// Types for the custom Vitest browser commands vitest.config.js registers (tests_js/_live_twin_command.js,
// _live_matrix_command.js, _lint_command.js, _port_lock.js): a `declare module` augmentation, which a runtime .js file
// cannot hold.

// `export {}` makes this a module, so the block below augments "vitest/browser" rather than replacing it (confirmed:
// without it the real `commands` export vanishes).
export {};

/** One process taking a port lock: in node through tests_js/_port_lock.js or in bash through scripts/_port_lock.sh. */
type PortLockActor = { lang: "node" | "bash"; port: number; runner: string; twice?: boolean; dropHeld?: boolean; then?: PortLockActor };

// Written out, not `typeof` imports: the implementations take Vitest's injected `ctx` first, which callers never pass,
// and an import would pull Node types into this browser program. Kept in step with each file's @returns.
declare module "vitest/browser" {
    interface BrowserCommands {
        runLiveBackendSmoke: (device: string, testTimeoutMs: number) => Promise<{
            titleHasSensorStation: boolean;
            deviceName: string;
            firstStatus: string | null;
            resubmitStatus: string | null;
            config: { inside: string[]; beside: string[]; left: string[] };
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
            field: import("./_expected_display.js").DisplayField;
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

