from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional

DEFAULT_SEED = 42
DEFAULT_DTYPE = np.float64


@dataclass
class DeterministicRNG:
    """Wrapper around Philox generator to enforce deterministic draws."""

    seed: int = DEFAULT_SEED
    bit_generator: Optional[np.random.BitGenerator] = None

    def __post_init__(self) -> None:
        if self.bit_generator is None:
            self.bit_generator = np.random.Philox(self.seed)
        self.generator = np.random.Generator(self.bit_generator)

    def normal(self, size, mean=0.0, std=1.0):
        return self.generator.normal(loc=mean, scale=std, size=size).astype(DEFAULT_DTYPE)

    def uniform(self, size, low=0.0, high=1.0):
        return self.generator.uniform(low=low, high=high, size=size).astype(DEFAULT_DTYPE)


def make_rng(seed: int = DEFAULT_SEED) -> DeterministicRNG:
    return DeterministicRNG(seed=seed)
