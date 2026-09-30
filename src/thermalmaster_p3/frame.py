from dataclasses import dataclass
from typing import Tuple

import numpy as np


def raw_to_celsius(raw: np.ndarray) -> np.ndarray:
    """Convert documented 1/64 K values; no environmental correction applied."""
    return np.asarray(raw, dtype=np.float32) / np.float32(64) - np.float32(273.15)


@dataclass(frozen=True)
class Frame:
    """Owned arrays and host reception times, not exposure timestamps."""

    raw: np.ndarray
    ir: np.ndarray
    metadata: np.ndarray
    sequence: int
    monotonic_ns: int
    utc_ns: int
    start_counters: Tuple[int, int, int]
    end_counters: Tuple[int, int, int]

    @property
    def temperature_c(self) -> np.ndarray:
        return raw_to_celsius(self.raw)
