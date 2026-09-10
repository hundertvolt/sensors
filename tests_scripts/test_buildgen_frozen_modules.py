"""Tests for buildgen.frozen_modules: dependency-driven frozen-module selection via AST-scanned
transitive import closure (BUILD_CHAIN_PLAN.md's "Core design decisions"), TYPE_CHECKING blocks
stripped, never a dynamic import."""

from pathlib import Path

import pytest

from buildgen.frozen_modules import CORE_MODULES, compute_frozen_modules
from buildgen.generate import generate_device


@pytest.fixture
def src_dir(repo_root: Path) -> Path:
    return repo_root / "src"


@pytest.fixture
def ext_dir(repo_root: Path) -> Path:
    return repo_root / "ext"


def test_wozi_frozen_modules_include_every_declared_driver(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    for driver_module in ("asy_scd30_driver", "asy_sgp40_driver", "asy_bmp3xx_driver", "asy_fram_manager", "asy_neopixel_driver", "asy_notification_service"):
        assert driver_module in result.frozen_modules


def test_frozen_modules_include_core_set(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert CORE_MODULES <= result.frozen_modules


def test_frozen_modules_include_transitive_dependency(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    # asy_sgp40_driver.py imports voc_algorithm.py and crc_checks.py directly - neither is in
    # CORE_MODULES nor a driver module itself, so this only passes if the transitive closure
    # actually walks imports, not just the seed set.
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "voc_algorithm" in result.frozen_modules
    assert "crc_checks" in result.frozen_modules


def test_frozen_modules_include_ext_microdot(repo_root: Path, src_dir: Path, ext_dir: Path) -> None:
    result = generate_device(repo_root / "devices" / "wozi.toml", src_dir, ext_dir)
    assert "microdot" in result.frozen_modules


def test_frozen_modules_exclude_type_checking_only_import(tmp_path: Path) -> None:
    # A module only reachable through an `if TYPE_CHECKING:` block never executes on-device
    # (MicroPython has no runtime typing module) - it must not be pulled into the closure.
    (tmp_path / "config_manager.py").write_text("")
    (tmp_path / "base_classes.py").write_text("")
    (tmp_path / "print_log.py").write_text("")
    (tmp_path / "api_response.py").write_text("")
    (tmp_path / "asy_i2c_driver.py").write_text("")
    (tmp_path / "asy_spi_driver.py").write_text("")
    (tmp_path / "asy_webserver_service.py").write_text("")
    (tmp_path / "asy_wifi_service.py").write_text("")
    (tmp_path / "asy_ntp_client.py").write_text("")
    (tmp_path / "asy_dns_client.py").write_text("")
    (tmp_path / "captive_dns.py").write_text("")
    (tmp_path / "system_service.py").write_text("")
    (tmp_path / "crc_checks.py").write_text("")
    (tmp_path / "type_only_dep.py").write_text("")
    (tmp_path / "asy_typechecked_driver.py").write_text(
        "try:\n    from typing import TYPE_CHECKING\nexcept ImportError:\n    TYPE_CHECKING = False\n\nif TYPE_CHECKING:\n    import type_only_dep\n"
    )

    from buildgen.driver_registry import DriverInfo
    from buildgen.model import DeviceModel, InstanceSpec

    model = DeviceModel("dev", tmp_path / "dev.toml", {})
    model.instances[("typechecked", "")] = InstanceSpec("typechecked", "", {}, {}, 0, DriverInfo("typechecked", "asy_typechecked_driver", "X", "sensor", tmp_path / "asy_typechecked_driver.py", False))

    frozen = compute_frozen_modules(model, tmp_path)
    assert "asy_typechecked_driver" in frozen
    assert "type_only_dep" not in frozen


def test_frozen_modules_real_import_is_included(tmp_path: Path) -> None:
    (tmp_path / "config_manager.py").write_text("")
    (tmp_path / "base_classes.py").write_text("")
    (tmp_path / "print_log.py").write_text("")
    (tmp_path / "api_response.py").write_text("")
    (tmp_path / "asy_i2c_driver.py").write_text("")
    (tmp_path / "asy_spi_driver.py").write_text("")
    (tmp_path / "asy_webserver_service.py").write_text("")
    (tmp_path / "asy_wifi_service.py").write_text("")
    (tmp_path / "asy_ntp_client.py").write_text("")
    (tmp_path / "asy_dns_client.py").write_text("")
    (tmp_path / "captive_dns.py").write_text("")
    (tmp_path / "system_service.py").write_text("")
    (tmp_path / "crc_checks.py").write_text("")
    (tmp_path / "real_dep.py").write_text("")
    (tmp_path / "asy_realdep_driver.py").write_text("import real_dep\n")

    from buildgen.driver_registry import DriverInfo
    from buildgen.model import DeviceModel, InstanceSpec

    model = DeviceModel("dev", tmp_path / "dev.toml", {})
    model.instances[("realdep", "")] = InstanceSpec("realdep", "", {}, {}, 0, DriverInfo("realdep", "asy_realdep_driver", "X", "sensor", tmp_path / "asy_realdep_driver.py", False))

    frozen = compute_frozen_modules(model, tmp_path)
    assert "real_dep" in frozen
