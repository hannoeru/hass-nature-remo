"""Tests for ECHONET Lite smart meter helpers."""

from custom_components.nature_remo import echonet


def test_parse_echonet_properties_accepts_numeric_strings() -> None:
    properties = echonet.parse_echonet_properties(
        [
            {"epc": "224", "val": "123"},
            {"epc": 225, "val": 0},
        ]
    )

    assert properties == {
        echonet.EPC_CUMULATIVE_CONSUMED_ENERGY: 123,
        echonet.EPC_CUMULATIVE_ENERGY_UNIT: 0,
    }


def test_calculate_cumulative_energy_applies_coefficient_and_unit() -> None:
    properties = {
        echonet.EPC_CUMULATIVE_CONSUMED_ENERGY: 123,
        echonet.EPC_COEFFICIENT: 2,
        echonet.EPC_CUMULATIVE_ENERGY_UNIT: 1,
    }

    assert (
        echonet.calculate_cumulative_energy(
            properties,
            echonet.EPC_CUMULATIVE_CONSUMED_ENERGY,
        )
        == 24.6
    )


def test_calculate_cumulative_energy_defaults_missing_coefficient_and_unit() -> None:
    properties = {echonet.EPC_CUMULATIVE_RETURNED_ENERGY: 42}

    assert (
        echonet.calculate_cumulative_energy(
            properties,
            echonet.EPC_CUMULATIVE_RETURNED_ENERGY,
        )
        == 42
    )


def test_calculate_cumulative_energy_returns_none_for_missing_epc() -> None:
    assert echonet.calculate_cumulative_energy({}, echonet.EPC_CUMULATIVE_RETURNED_ENERGY) is None


def test_has_epc() -> None:
    properties = {echonet.EPC_CUMULATIVE_RETURNED_ENERGY: 10}

    assert echonet.has_epc(properties, echonet.EPC_CUMULATIVE_RETURNED_ENERGY)
    assert not echonet.has_epc(properties, echonet.EPC_CUMULATIVE_CONSUMED_ENERGY)
