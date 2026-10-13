"""Home Assistant harness fixtures for the Nature Remo integration."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load this repository as a custom integration."""


@pytest.fixture
def hass_config_dir(tmp_path: Path) -> str:
    """Point Home Assistant at a config dir that contains this integration."""
    custom_components = tmp_path / "custom_components"
    custom_components.mkdir()
    (custom_components / "__init__.py").write_text("")
    source = ROOT / "custom_components" / "nature_remo"
    (custom_components / "nature_remo").symlink_to(source, target_is_directory=True)
    return str(tmp_path)
