"""Map repo paths to their owning audit area (PROJECT_AUDIT_PLAN.md 5.0) or to the 2.2 reference list.

Usage: owner_of.py [path ...]  (no args: every tracked file). Temporary; deleted with the audit.
"""

import fnmatch
import subprocess
import sys

# One row per 5.0 entry; keep in step with the plan's table (validate_plan.py checks the result).
AREAS = {
    "CORE": ["src/system_service.py", "src/base_classes.py", "src/config_manager.py", "src/print_log.py", "src/api_response.py"],
    "ALGO": ["src/math_helpers.py", "src/voc_algorithm.py", "src/crc_checks.py", "src/framing_codecs.py"],
    "BUS": ["src/asy_i2c_driver.py", "src/asy_spi_driver.py", "src/asy_uart_driver.py"],
    "SENS": ["src/asy_scd30_driver.py", "src/asy_sgp40_driver.py", "src/asy_bmp3xx_driver.py", "src/asy_isl29125_driver.py"],
    "STOR": ["src/asy_fram_driver.py", "src/asy_fram_manager.py"],
    "UART": ["src/asy_uart_comm.py", "src/asy_uart_link_driver.py", "UART_C_PORT_CHANGELOG.md"],
    "NET": ["src/asy_wifi_service.py", "src/asy_ntp_client.py", "src/asy_dns_client.py", "src/asy_udp_socket.py", "src/captive_dns.py", "src/LICENSE-captive_dns"],
    "REST": ["src/asy_webserver_service.py", "ext/microdot.py"],
    "LED": ["src/asy_neopixel_driver.py", "src/asy_notification_service.py"],
    "GEN": ["buildgen/*", "devices/*.toml"],
    "TOOL": ["toolchain/*"],
    "SCR": ["scripts/*", "host_typecheck.ini", "digital_twin/typecheck.ini"],
    "CI": [".github/*", "pyproject.toml", "uv.lock", "package.json", "package-lock.json", ".nvmrc", ".gitignore", "eslint.config.js", "tsconfig*.json", "vitest.config.js", ".htmlvalidate.json", ".stylelintrc.json"],
    "WEB": ["js/*", "html/*", "mockdata/*", "ext/freezefs/*.py"],
    "TEST": ["tests/*", "tests_scripts/*", "tests_js/*"],
    "TWIN": ["digital_twin/*"],
    "HW": ["tests_hardware/*", "REAL_HARDWARE_TEST_QUEUE.md", "HARDWARE_TEST_HANDOVER.md", "HEAP_FRAGMENTATION_MEASUREMENTS.md", "dev_legacy/README.md"],
    "DOC": ["README.md", "SPECIFICATION.md", "CLAUDE.md", "BACKLOG.md", "DEVICE_REFERENCE.md", "PROJECT_AUDIT_PLAN.md", "update_and_install.txt"],
    "LIC": ["LICENSE", "THIRD_PARTY_LICENSES.md", "ext/LICENSE-microdot", "ext/freezefs/LICENSE"],
    "ENV": ["audit/*"],
}
EXCEPT = {"TWIN": ["digital_twin/typecheck.ini"]}
REFERENCE = ["arduino/*", "python/*", "modules/*", "build-*.sh", "html_raw/*", "datasheets/*", "dev_legacy/*"]


def owners(path):
    """Every area whose patterns match path (fnmatch's * crosses '/'); a sound table yields one."""
    hits = []
    for area, pats in AREAS.items():
        if any(fnmatch.fnmatchcase(path, p) for p in pats) and path not in EXCEPT.get(area, []):
            hits.append(area)
    return hits


def classify(path):
    hits = owners(path)
    if hits:
        return hits
    return ["REFERENCE"] if any(fnmatch.fnmatchcase(path, p) for p in REFERENCE) else []


if __name__ == "__main__":
    paths = sys.argv[1:] or subprocess.check_output(["git", "ls-files"], text=True).split("\n")
    for p in filter(None, paths):
        print(f"{','.join(classify(p)) or 'UNOWNED'}\t{p}")
