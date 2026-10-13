---
name: verify
description: >
  Prove the Nature Remo Home Assistant integration the way a user would.

  TRIGGER THIS SKILL WHEN:
  - Changing custom_components/nature_remo, its tests, dependencies, or CI
  - Asked to verify, reproduce, or explain whether Nature Remo works in Home Assistant
  - Preparing a pull request that should show the integration still loads

  SYMPTOMS:
  - Agent only runs a unit test and never loads the integration in Home Assistant
  - Agent mocks entity classes instead of the Nature Remo HTTP API
  - Agent skips ruff, mypy, or pytest before calling a change done
---

# Verify Nature Remo

Run these steps from the repository root. They are the same checks CI runs, plus a Home Assistant harness that creates the entities a user would see.

Requires Python 3.14.2 or newer and [uv](https://docs.astral.sh/uv/).

## 1. Install the project

```sh
uv sync --dev
```

This installs Home Assistant, the integration's runtime dependencies, and `pytest-homeassistant-custom-component` from the dev group in `pyproject.toml`. That plugin is pinned to the release that tracks the Home Assistant version in `hacs.json` (currently 2026.10.1, plugin 0.13.372). Move the pin and Home Assistant together; a newer plugin requires a newer Home Assistant. pytest stays at 9.0.3 because that plugin release requires it.

## 2. Lint and type-check

```sh
uv run ruff check
uv run ruff format --check
uv run mypy -p custom_components.nature_remo
```

`ruff format --check` fails when a file would be rewritten. Format with `uv run ruff format` only when that is the change you intend to commit.

## 3. Run the tests

```sh
uv run pytest
```

Pytest includes the unit tests and the Home Assistant harness. The harness plugin is installed as a pytest entry point, so it is active for the whole suite. `asyncio_mode` is `auto` in `pyproject.toml` because that plugin's fixtures are async.

## 4. Home Assistant harness

`tests/harness/test_setup.py` loads `custom_components/nature_remo` inside a real Home Assistant core test instance. It does not talk to Nature Remo's cloud. `aioclient_mock` answers:

- `GET https://api.nature.global/1/appliances`
- `GET https://api.nature.global/1/devices`

Payloads live in `tests/harness/payloads.py`. The sample account has an air conditioner, a smart meter, an IR switch, a light, a TV, and a Remo device that is not attached to an appliance.

The tests then:

1. Create a config entry with an access token and the default cool/heat temperatures, the same data the settings UI stores.
2. Wait for the first coordinator refresh.
3. Assert the climate, power, energy, switch, light, media player, and room sensor entities exist and carry the mocked values. Home Assistant builds the entity id from the device name and the entity name, for example `climate.living_room_nature_remo_living_ac`. Assert the id Home Assistant registered. Numeric sensor states are strings such as `450.0`. The climate entity's current temperature stays unknown until a later coordinator refresh, so the harness does not assert it.
4. Assert the request used `Authorization: Bearer <token>`.
5. Unload the config entry and assert it is no longer loaded. Home Assistant may leave the entity id in the state machine as `unavailable`.
6. Walk the user config flow for a valid token and for an HTTP 401.

Run only the harness while iterating:

```sh
uv run pytest tests/harness
```

The coordinator's 60 second update interval is still scheduled after unload, so the harness allows lingering timers. Do not copy that marker onto tests that should prove a timer was cancelled.

To cover a new API response, add or override the payload, register it on `aioclient_mock` before setup, and assert the Home Assistant state a user would see. Prefer that over constructing entity classes directly when the bug is in setup, discovery, or config flow.

## 5. One command

```sh
scripts/verify.sh
```

The script syncs dependencies, then runs ruff, mypy, and pytest. Use it before opening or merging a change.

## When a check fails

- Ruff or mypy: fix the integration code the diagnostic names. Do not silence a new error with a broad ignore.
- A harness assertion: read the mocked payload and the entity state together. A missing entity usually means setup filtered that appliance or device out.
- `No mock registered for GET https://api.nature.global/...`: the code called an endpoint the test did not stub. Add the stub or stop the extra call.
- An HTTP 401 in the user flow is reported as `cannot_connect` on the form. The flow must not create a config entry.
