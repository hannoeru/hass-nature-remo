# Home Assistant integration for Nature Remo

[![CI](https://github.com/hannoeru/hass-nature-remo/actions/workflows/ci.yml/badge.svg)](https://github.com/hannoeru/hass-nature-remo/actions/workflows/ci.yml)
[![Release](https://github.com/hannoeru/hass-nature-remo/actions/workflows/release.yml/badge.svg)](https://github.com/hannoeru/hass-nature-remo/actions/workflows/release.yml)
[![GitHub release](https://img.shields.io/github/v/release/hannoeru/hass-nature-remo)](https://github.com/hannoeru/hass-nature-remo/releases)

A custom [Home Assistant](https://www.home-assistant.io) integration for [Nature Remo](https://en.nature.global/en/).

This repository is a fork of [yutoyazaki/hass-nature-remo](https://github.com/yutoyazaki/hass-nature-remo), updated for current Home Assistant and HACS requirements.

> [!WARNING]
> This integration is neither Nature Remo official nor Home Assistant official. **Use at your own risk.**

<img src="https://raw.githubusercontent.com/hannoeru/hass-nature-remo/main/assets/screenshot_1.png" width="600">
<img src="https://raw.githubusercontent.com/hannoeru/hass-nature-remo/main/assets/screenshot_2.png" width="200">

## Features

| Nature Remo appliance/device | Home Assistant platform | Status |
| --- | --- | --- |
| Air conditioner | `climate` | Supported |
| Nature Remo E / E Lite smart meter | `sensor` | Supported, Energy Dashboard compatible |
| Generic IR appliance | `switch` | Supported with assumed state |
| Light | `light` | Supported with assumed state |
| TV | `media_player` | Supported with assumed state |
| Nature Remo environmental sensors | `sensor` | Temperature, humidity, illuminance |

### Air conditioner

- Set HVAC mode, such as cool, heat/warm, dry, fan/blow, and auto
- Set target temperature
- Set fan mode
- Set swing mode
- Show current temperature from the associated Nature Remo device
- Remember previous target temperatures when switching modes back and forth

### Energy sensors

For Nature Remo E and E Lite:

- Current power usage
- Cumulative consumed energy
- Cumulative returned energy, for solar panels and similar setups
- Home Assistant Energy Dashboard metadata

### IR appliances

- Generic IR appliances are exposed as `switch` entities when on/off/toggle signals are available
- Lights are exposed as `light` entities using Nature Remo light buttons and state
- TVs are exposed as `media_player` entities using Nature Remo TV buttons and input state

## Compatibility and testing status

- Compatibility target: **Home Assistant Core 2026.5.3**
- Energy sensor features, including cumulative consumed and returned energy, have been tested against real hardware
- Air conditioner, switch, light, and TV entities are unit-tested but were not verified against physical devices in this update

## Known limitations

- IR-based appliances use **assumed state** because Nature Remo sends infrared commands and may not know the real device state
- Switch support depends on registered signal icons in the Nature Remo app (`ico_on`, `ico_off`, or `ico_io`)
- Light and TV support depends on the buttons exposed by Nature Remo's Cloud API for the appliance model
- YAML configuration is supported only for backward-compatible import; new setups should use the Home Assistant UI

## Home Assistant Energy Dashboard support

This integration supports Home Assistant's [Energy Dashboard](https://www.home-assistant.io/docs/energy/).
If you use Nature Remo E or E Lite, cumulative consumed and returned energy sensors are automatically configured with the required device class, state class, and unit metadata so they can be selected in the Energy Dashboard.

## Installation

### HACS custom repository

1. Open HACS in Home Assistant
2. Go to **Custom repositories**
3. Add this repository:
   - Repository: `https://github.com/hannoeru/hass-nature-remo`
   - Category: `Integration`
4. Install **Nature Remo**
5. Restart Home Assistant

See the HACS documentation for more details: [Custom repositories](https://hacs.xyz/docs/faq/custom_repositories/).

### Manual installation

1. Download this repository
2. Copy `custom_components/nature_remo` into your Home Assistant configuration directory
3. Restart Home Assistant

Expected result:

```text
{path_to_your_config}
├── configuration.yaml
└── custom_components
    └── nature_remo
        ├── __init__.py
        ├── climate.py
        ├── config_flow.py
        ├── echonet.py
        ├── light.py
        ├── manifest.json
        ├── media_player.py
        ├── sensor.py
        ├── switch.py
        └── translations/
```

### Git submodule installation

If you manage your Home Assistant configuration in git, you can install this repository as a submodule and symlink the integration directory:

```sh
git submodule add https://github.com/hannoeru/hass-nature-remo.git vendor/hass-nature-remo
ln -s ../../vendor/hass-nature-remo/custom_components/nature_remo custom_components/nature_remo
```

## Configuration

1. Go to <https://home.nature.global>
2. Sign in or create an account
3. Generate a Nature Remo access token
4. In Home Assistant, go to **Settings → Devices & services → Add integration**
5. Search for **Nature Remo**
6. Enter your access token

### Legacy YAML import

Existing YAML configuration is imported automatically on startup:

```yaml
nature_remo:
  access_token: YOUR_ACCESS_TOKEN
```

After import, prefer managing the integration from **Settings → Devices & services**.

## Troubleshooting

### Enable debug logging

Add this to your Home Assistant `configuration.yaml`, then restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.nature_remo: debug
```

### Things to check

- Confirm the Nature Remo access token is valid
- Confirm the appliance is visible in the Nature Remo app
- For IR switches, confirm the appliance has an on/off/toggle signal registered in Nature Remo
- For lights and TVs, confirm the appliance is registered as a Light or TV in Nature Remo, not only as a generic IR appliance
- Check Home Assistant logs for messages from `custom_components.nature_remo`

## Development

### Prerequisites

- Python 3.14.2 or higher
- [uv](https://docs.astral.sh/uv/)

### Setup

```sh
git clone https://github.com/hannoeru/hass-nature-remo.git
cd hass-nature-remo
uv sync --dev
```

### Quality checks

```sh
uv run ruff check
uv run ruff format --check
uv run mypy -p custom_components.nature_remo
uv run pytest
```

### Project structure

```text
hass-nature-remo/
├── .github/workflows/                 # CI, HACS/hassfest validation, and release packaging
├── brand/icon.png                     # HACS/Home Assistant brand icon
├── custom_components/nature_remo/     # HACS integration package
│   ├── __init__.py                    # Main integration setup
│   ├── climate.py                     # Climate entity implementation
│   ├── config_flow.py                 # UI setup and YAML import flow
│   ├── echonet.py                     # ECHONET Lite smart-meter helpers
│   ├── light.py                       # Light entity implementation
│   ├── manifest.json                  # Home Assistant integration manifest
│   ├── media_player.py                # TV media player entity implementation
│   ├── sensor.py                      # Sensor entities implementation
│   ├── switch.py                      # Generic IR switch entity implementation
│   └── translations/                  # Integration translations
├── hacs.json                          # HACS metadata
├── pyproject.toml                     # Project configuration and dependencies
├── README.md                          # This file
└── tests/                             # Tests
```

### Release flow

Releases are handled by GitHub Actions:

1. Update `custom_components/nature_remo/manifest.json`'s `version`
2. Commit and push the version bump
3. Create and push a matching tag, for example `v0.6.2` for version `0.6.2`
4. The release workflow creates/updates the GitHub release and uploads `nature_remo.zip` for HACS

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the quality checks
5. Open a pull request

Please include tests for new behavior where practical.
