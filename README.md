# Home Assistant integration for Nature Remo

Yet another [Home Assistant](https://www.home-assistant.io) component for [Nature Remo](https://en.nature.global/en/).

⚠️This integration is neither Nature Remo official nor Home Assistant official. **Use at your own risk.** ⚠️

<img src="https://raw.githubusercontent.com/hannoeru/hass-nature-remo/main/assets/screenshot_1.png" width="600">
<img src="https://raw.githubusercontent.com/hannoeru/hass-nature-remo/main/assets/screenshot_2.png" width="200">

## Supported features

- [x] Air Conditioner
  - [x] Set mode (e.g. cool, warm, blow etc.)
  - [x] Set temperature
  - [x] Set fan mode
  - [x] Set swing mode
  - [x] Show current temperature
  - [x] Remember previous target temperatures when switching modes back and forth
- [x] Energy Sensor (Nature Remo E/E Lite)
  - [x] Fetch current power usage
  - [x] Fetch cumulative consumed energy
  - [x] Fetch cumulative returned energy (for solar panels, etc.)
- [ ] Switch
- [ ] Light
- [ ] TV
- [x] Others
  - [x] Fetch sensor data

Compatibility target: Home Assistant Core 2026.5.3.
Only energy sensor features (including cumulative consumed and returned energy) have been tested.
Other device features (e.g. air conditioners, switches) were not verified in this update.

## Home Assistant Energy Dashboard support

This integration supports Home Assistant's [Energy Dashboard](https://www.home-assistant.io/docs/energy/).
If you're using Nature Remo E or E Lite, cumulative energy sensors (both consumed and returned) will automatically be available for configuration.

## Installation

### Install via HACS Custom repositories

https://hacs.xyz/docs/faq/custom_repositories

Enter the following information in the dialog and click `Add` button.

- Repository: https://github.com/hannoeru/hass-nature-remo
- Category: Integrations

### Manual Install

1. Download this repository
1. Create `custom_components/nature_remo` folder in your config directory
1. Copy files into it (Just drag&drop whole files would be fine)

```
{path_to_your_config}
├── configuration.yaml
└── custom_components
    └── nature_remo
        ├── __init__.py
        ├── climate.py
        ├── config_flow.py
        ├── echonet.py
        ├── manifest.json
        ├── sensor.py
        └── translations/
```

### Install via git submodule

If you have set up git, you can also install this component by adding submodule to your git repository.

```sh
git submodule add https://github.com/yutoyazaki/hass-nature-remo.git {path_to_custom_component}/nature_remo
```

## Configuration

1. Go to https://home.nature.global and sign in/up
1. Generate an access token
1. In Home Assistant, go to **Settings → Devices & services → Add integration**
1. Search for **Nature Remo** and enter your access token

Existing YAML configuration is imported automatically on startup:

```yaml
nature_remo:
  access_token: YOUR_ACCESS_TOKEN
```

## Development

This section contains information for developers who want to contribute to this project.

### Prerequisites

- Python 3.14.2 or higher
- [uv](https://docs.astral.sh/uv/) - Python package manager

### Setup Development Environment

1. **Clone the repository**
   ```bash
   git clone https://github.com/hannoeru/hass-nature-remo.git
   cd hass-nature-remo
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Set up virtual environment and install dependencies**
   ```bash
   uv sync --dev
   ```

4. **Activate the virtual environment**
   ```bash
   source .venv/bin/activate
   ```

### Development Tools

This project uses several development tools to maintain code quality:

#### Code Linting and Formatting

- **Ruff** - Fast Python linter and formatter
  ```bash
  # Check for linting issues
  uv run ruff check

  # Fix auto-fixable issues
  uv run ruff check --fix

  # Format code
  uv run ruff format
  ```

#### Type Checking

- **mypy** - Static type checker
  ```bash
  uv run mypy .
  ```

#### Testing

- **pytest** - Testing framework
  ```bash
  # Run all tests
  uv run pytest

  # Run tests with coverage
  uv run pytest --cov

  # Run specific test file
  uv run pytest tests/test_specific.py
  ```

### Release Flow

This repository uses GitHub Actions for release safety:

- `CI` runs Ruff, mypy, pytest, HACS validation, and Home Assistant hassfest validation on pushes and pull requests.
- `Release` runs when a GitHub release is published, verifies the release tag matches `manifest.json`'s `version`, and uploads `nature_remo.zip` as the HACS `zip_release` artifact declared in `hacs.json`.

To publish a release:

1. Update `manifest.json`'s `version`.
2. Create and publish a matching GitHub release tag, for example `v0.1.0` for version `0.1.0`.
3. Confirm the release workflow attached `nature_remo.zip` to the release.

### Project Structure

```
hass-nature-remo/
├── __init__.py          # Main integration setup
├── climate.py           # Climate entity implementation
├── .github/workflows/   # CI, HACS/hassfest validation, and release packaging
├── config_flow.py       # UI setup and YAML import flow
├── echonet.py           # ECHONET Lite smart-meter helpers
├── sensor.py            # Sensor entities implementation
├── manifest.json        # Home Assistant integration manifest
├── pyproject.toml       # Project configuration and dependencies
├── README.md            # This file
└── tests/               # Test files (if any)
```

### Adding New Features

1. **Follow Home Assistant development patterns** - Refer to the [Home Assistant Developer Documentation](https://developers.home-assistant.io/)

2. **Add type annotations** - All new code should include proper type hints

3. **Write tests** - Add tests for new functionality in the `tests/` directory

4. **Run quality checks** before committing:
   ```bash
   # Run all checks
   uv run ruff check --fix
   uv run ruff format
   uv run mypy .
   uv run pytest
   ```

### Debugging

For debugging the integration:

1. **Enable debug logging** in your Home Assistant `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.nature_remo: debug
   ```

2. **Use Home Assistant's developer tools** to inspect entity states and attributes

3. **Check Home Assistant logs** for any error messages related to the integration

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the development guidelines above
4. Run all quality checks
5. Submit a pull request

### Home Assistant Integration Testing

To test the integration with Home Assistant:

1. **Install Home Assistant** in a development environment
2. **Copy the integration** to your `custom_components` directory
3. **Add the configuration** to your `configuration.yaml`
4. **Restart Home Assistant** and check the logs for any issues
