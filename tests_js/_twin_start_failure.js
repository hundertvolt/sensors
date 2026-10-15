// Why a spawned twin can no longer start serving, or null while it still can: the live commands
// check it on every readiness poll, so a spawn error or an early exit is named, not waited out.

/**
 * @param {{ spawnError: Error | null, exitCode: number | null, signalCode: string | null }} state
 * @returns {string | null}
 */
export function twinStartFailure(state) {
    if (state.spawnError !== null) {
        return `the digital twin failed to start: ${state.spawnError.message}`;
    }
    if (state.exitCode !== null || state.signalCode !== null) {
        return `the digital twin exited before serving (exit code ${state.exitCode ?? "none"}, signal ${state.signalCode ?? "none"})`;
    }
    return null;
}
