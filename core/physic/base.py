import math
from typing import TYPE_CHECKING

from core import models


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.world import SimulationWorld
    from simulator.creature import SimulationCreature


class WorldCharacteristics:
    """Физические характеристики мира."""

    db_model = models.WorldCharacteristics
    db_instance: db_model

    def __init__(self, viscosity: float, borders_friction: float, borders_thickness: int, resource_density: float):
        # вязкость
        # 1 - объекты теряют всю скорость после каждого тика
        # 0 - не теряют скорости вообще
        if not 0 <= viscosity <= 1:
            raise ValueError(f"Viscosity must belong to [0, 1], but {viscosity} was given")
        self.viscosity = viscosity
        self.borders_friction = borders_friction
        self.borders_thickness = borders_thickness
        self.resource_density = resource_density

    def __repr__(self) -> str:
        string = f"viscosity: {self.viscosity}, borders friction: {self.borders_friction}, "
        string += f"borders thickness: {self.borders_thickness}, resources coef: {self.resource_density}"
        return string

    def save_to_db(self, world: "SimulationWorld"):
        self.db_instance = self.db_model(
            world = world.db_instance,
            viscosity = self.viscosity,
            borders_friction = self.borders_friction,
            borders_thickness = self.borders_thickness,
            resource_coeff = self.resource_density
        )
        self.db_instance.save()


class CreatureCharacteristics:
    def __init__(self, creature: "SimulationCreature") -> None:
        self.creature = creature
        if not 0 <= self.creature.genome.effects.elasticity <= 1:
            raise ValueError(
                f"Elasticity must belong to [0, 1], but {self.creature.genome.effects.elasticity} was given"
            )
        self.elasticity = self.creature.genome.effects.elasticity
        self.size_coeff = self.creature.genome.effects.size_coeff

    def __repr__(self) -> str:
        string = (f"elasticity: {self.elasticity}, size coef: {self.size_coeff}, radius: {self.radius}, "
                  f"volume: {self.volume}, mass: {self.mass}")
        return string

    # объем == площадь
    @property
    def radius(self) -> float:
        return math.sqrt(self.volume / math.pi)

    # объем == площадь
    @property
    def volume(self) -> float:
        return sum(bodypart.volume for bodypart in self.creature.bodyparts)

    @property
    def mass(self) -> float:
        return sum(bodypart.mass for bodypart in self.creature.bodyparts)
