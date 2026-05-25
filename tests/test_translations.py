"""Tests for integration translation files."""

import json
from pathlib import Path
from typing import Any

TRANSLATIONS = Path(__file__).parents[1] / "custom_components" / "nature_remo" / "translations"
REQUIRED_TRANSLATIONS = {"en.json", "ja.json", "zh-Hant.json"}


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_flatten_keys(value, path))
        else:
            keys.add(path)
    return keys


def test_required_translation_files_exist() -> None:
    assert REQUIRED_TRANSLATIONS <= {path.name for path in TRANSLATIONS.glob("*.json")}


def test_translation_files_have_matching_keys() -> None:
    english = json.loads((TRANSLATIONS / "en.json").read_text())
    expected_keys = _flatten_keys(english)

    for path in TRANSLATIONS.glob("*.json"):
        data = json.loads(path.read_text())
        assert _flatten_keys(data) == expected_keys, path.name
