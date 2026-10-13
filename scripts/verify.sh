#!/usr/bin/env bash
# Prove the Nature Remo integration the way CI and a Home Assistant user would.
set -euo pipefail

cd "$(dirname "$0")/.."

uv sync --dev
uv run ruff check
uv run ruff format --check
uv run mypy -p custom_components.nature_remo
uv run pytest
