from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

# Fixed namespace so uuid5 results stay stable across runs/machines.
SEED_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")


@dataclass(slots=True)
class SeededRNG:
    seed: int
    rng: random.Random

    @classmethod
    def create(cls, seed: int) -> SeededRNG:
        return cls(seed=seed, rng=random.Random(seed))

    def uuid(self, kind: str, key: str) -> uuid.UUID:
        return uuid.uuid5(SEED_NAMESPACE, f"{self.seed}:{kind}:{key}")

    def choice[T](self, seq: list[T] | tuple[T, ...]) -> T:
        return self.rng.choice(seq)

    def sample[T](self, population: list[T], k: int) -> list[T]:
        if k <= 0 or not population:
            return []
        k = min(k, len(population))
        return self.rng.sample(population, k)

    def randint(self, a: int, b: int) -> int:
        return self.rng.randint(a, b)

    def random(self) -> float:
        return self.rng.random()

    def chance(self, p: float) -> bool:
        return self.rng.random() < p
