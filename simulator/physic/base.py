import copy
import math
from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.bodypart import BaseBodypart
    from simulator.object.creature.genome import GenomeEffects


class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.to_tuple())

    def __add__(self, other) -> "Vector":
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other) -> "Vector":
        return Vector(self.x - other.x, self.y - other.y)

    def round(self) -> "Vector":
        return Vector(int(self.x), int(self.y))

    def to_tuple(self):
        return self.x, self.y

    def reset(self):
        self.x = 0
        self.y = 0

    def accumulate(self, x, y):
        self.x += x
        self.y += y

    def multiply(self, multiplier) -> "Vector":
        return self.__class__(self.x * multiplier, self.y * multiplier)

    def multiply_ip(self, multiplier) -> "Vector":
        self.x = self.x * multiplier
        self.y = self.y * multiplier
        return self

    def divide(self, divider) -> "Vector":
        return self.__class__(self.x / divider, self.y / divider)

    def divide_ip(self, divider) -> "Vector":
        self.x = self.x / divider
        self.y = self.y / divider
        return self

    def less_then(self, number) -> bool:
        return abs(self.x) < number and abs(self.y) < number

    def copy(self) -> "Vector":
        return copy.deepcopy(self)


class BaseWorldCharacteristics:
    def __init__(self, viscosity):
        # вязкость
        self.viscosity = viscosity


class BaseCreatureCharacteristics:
    def __init__(
            self,
            bodyparts: list["BaseBodypart"],
            genome_effects: "GenomeEffects",
            world_characteristics: BaseWorldCharacteristics,
    ):
        self.bodyparts = bodyparts
        self.genome_effects = genome_effects
        self.elasticity = genome_effects.elasticity
        self.size = self.genome_effects.size
        self.world_characteristics = world_characteristics
        # сила (сумма сил), с которой действуют на объект в данный тик
        self.force = Vector(0, 0)
        self.speed = Vector(0, 0)
        self.accumulated_movement = Vector(0, 0)

    @property
    def radius(self) -> int:
        return int(math.sqrt(self.volume / math.pi))

    @property
    def mass(self) -> float:
        return sum([bodypart.mass for bodypart in self.bodyparts])

    # объем == площадь
    @property
    def volume(self) -> float:
        return sum([bodypart.volume for bodypart in self.bodyparts])

    @property
    def movement(self) -> Vector:
        ticks = 1
        return Vector(self.speed.x * ticks, self.speed.y * ticks) + self.accumulated_movement

    def update_speed(self):
        ticks = 1
        self.speed.accumulate(
            self.force.x * ticks / self.mass,
            self.force.y * ticks / self.mass
        )
        self.speed.divide_ip(1 + self.world_characteristics.viscosity * self.volume / 1000)
        if self.speed.less_then(0.05 * self.world_characteristics.viscosity):
            self.speed.reset()

    def update_force(self):
        self.force.reset()

    def update_accumulated_movement(self):
        self.accumulated_movement = self.movement - self.movement.round()
