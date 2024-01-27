import math
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from simulator.creature import Creature


class CreatureCharacteristics:
    def __init__(self, creature: "Creature") -> None:
        self.creature = creature
        if not 0 <= self.creature.genome.effects.elasticity <= 1:
            raise ValueError(
                f"Elasticity must belong to [0, 1], but {self.creature.genome.effects.elasticity} was given"
            )
        self.elasticity = self.creature.genome.effects.elasticity
        self.size_coeff = self.creature.genome.effects.size_coeff

        self.volume = sum(bodypart.volume for bodypart in self.creature.bodyparts)
        self.radius = (3 / 4 * self.volume / math.pi)**(1 / 3)
        self._mass: float | None = None

    def __repr__(self) -> str:
        return (f"elasticity: {self.elasticity}, size coef: {self.size_coeff}, radius: {self.radius}, "
                f"volume: {self.volume}, mass: {self.mass}")

    @property
    def mass(self) -> float:
        if self._mass is None:
            self._mass = sum(bodypart.mass for bodypart in self.creature.bodyparts)
        return self._mass
