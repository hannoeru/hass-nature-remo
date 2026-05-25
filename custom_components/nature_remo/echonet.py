"""Helpers for Nature Remo ECHONET Lite smart meter properties."""

from collections.abc import Iterable, Mapping
from typing import Any

EPC_COEFFICIENT = 211
EPC_CUMULATIVE_CONSUMED_ENERGY = 224
EPC_CUMULATIVE_ENERGY_UNIT = 225
EPC_CUMULATIVE_RETURNED_ENERGY = 227
EPC_MEASURED_INSTANTANEOUS_POWER = 231

CUMULATIVE_ENERGY_UNIT_TABLE: dict[int, float] = {
    0: 1,
    1: 0.1,
    2: 0.01,
    3: 0.001,
    4: 0.0001,
    10: 10,
    11: 100,
    12: 1000,
}


def parse_echonet_properties(properties: Iterable[Mapping[str, Any]]) -> dict[int, float]:
    """Parse Nature Remo ECHONET Lite properties by EPC code."""
    return {int(prop["epc"]): float(prop["val"]) for prop in properties}


def has_epc(properties: Mapping[int, float], epc: int) -> bool:
    """Return whether an EPC code exists in parsed properties."""
    return epc in properties


def calculate_cumulative_energy(properties: Mapping[int, float], epc: int) -> float | None:
    """Calculate cumulative energy in kWh for an EPC code."""
    if epc not in properties:
        return None

    value = properties[epc]
    coefficient = properties.get(EPC_COEFFICIENT, 1)
    unit_code = int(properties.get(EPC_CUMULATIVE_ENERGY_UNIT, 0))
    unit = CUMULATIVE_ENERGY_UNIT_TABLE.get(unit_code, 1)
    return value * coefficient * unit
