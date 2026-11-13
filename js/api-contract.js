/**
 * Wire facts mirrored from src/ (SPECIFICATION.md Part G's mirror obligation): the four PUT result words, the
 * error-count cap, the degraded-source marker and the time-struct keys. tests_scripts/test_js_api_mirrors.py pins
 * each against its Python source.
 */

export const VALID = "Valid"; // src/asy_config_manager.py's VALID
export const UNCHANGED = "Unchanged"; // src/asy_config_manager.py's UNCHANGED
export const INVALID = "Invalid"; // src/asy_config_manager.py's INVALID
export const FAILED = "Failed"; // src/asy_config_manager.py's FAILED

export const ERR_COUNT_CAP = 65535; // src/asy_print_log.py's _MAX_CNT: the error counter's saturation value

// The first six keys of _gmtimestruct_to_dict() in the generated module (buildgen/codegen.py emits it).
export const GMTIME_KEYS = ["Year", "Month", "MDay", "Hour", "Minute", "Second"];

/**
 * The degraded-source marker src/asy_webserver_service.py's _write_guarded() and _write_errcount_entry()
 * send in place of a source's values: exactly `{"error": "unavailable"}`, never the marker beside other keys.
 * @param {unknown} value
 * @returns {boolean}
 */
export function isUnavailable(value) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return false;
    }
    const keys = Object.keys(value);
    return keys.length === 1 && keys[0] === "error" && /** @type {{error: unknown}} */ (value).error === "unavailable";
}
