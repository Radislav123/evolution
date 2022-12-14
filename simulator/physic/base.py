import math
from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.creature.bodypart import BaseBodypart
    from simulator.creature.genome import GenomeEffects


class BaseWorldCharacteristics:
    def __init__(self, viscosity: float, borders_friction: float, borders_thickness: int, resource_coef: float):
        # вязкость
        # 1 - объекты теряют всю скорость после каждого тика
        # 0 - не теряют скорости вообще
        if not 0 <= viscosity <= 1:
            raise ValueError(f"Viscosity must belong to [0, 1], but {viscosity} was given")
        self.viscosity = viscosity
        self.borders_friction = borders_friction
        self.borders_thickness = borders_thickness
        self.resource_coef = resource_coef

    def __repr__(self) -> str:
        string = f"viscosity: {self.viscosity}, borders friction: {self.borders_friction}, "
        string += f"borders thickness: {self.borders_thickness}, resources coef: {self.resource_coef}"
        return string


class BaseCreatureCharacteristics:
    def __init__(
            self,
            bodyparts: list["BaseBodypart"],
            genome_effects: "GenomeEffects",
            world_characteristics: BaseWorldCharacteristics,
    ):
        self.bodyparts = bodyparts
        self.genome_effects = genome_effects
        if not 0 <= genome_effects.elasticity <= 1:
            raise ValueError(f"Elasticity must belong to [0, 1], but {genome_effects.elasticity} was given")
        self.elasticity = genome_effects.elasticity
        self.size_coef = self.genome_effects.size_coef
        self.world_characteristics = world_characteristics

    def __repr__(self) -> str:
        string = f"elasticity: {self.elasticity}, size coef: {self.size_coef}, radius: {self.radius}, "
        string += f"volume: {self.volume}, mass: {self.mass}"
        return string

    @property
    def radius(self) -> float:
        return math.sqrt(self.volume / math.pi)

    # объем == площадь
    @property
    def volume(self) -> float:
        return sum([bodypart.volume for bodypart in self.bodyparts])

    @property
    def mass(self) -> float:
        return sum([bodypart.mass for bodypart in self.bodyparts])
