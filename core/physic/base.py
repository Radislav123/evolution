from typing import TYPE_CHECKING


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.storage.base import BaseSimulationStorage


class Vector:
    def __init__(self, x = 0, y = 0):
        self.x = x
        self.y = y

    def __str__(self):
        return str(self.to_tuple())

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

    def less_then(self, number):
        return abs(self.x) < number and abs(self.y) < number


class BaseWorldCharacteristics:
    def __init__(self, viscosity):
        # вязкость
        self.viscosity = viscosity


class BaseCreatureCharacteristics:
    def __init__(
            self,
            mass,
            volume,
            elasticity,
            world_characteristics: BaseWorldCharacteristics,
            creature_storage: "BaseSimulationStorage"
    ):
        self._mass = mass
        # объем
        self.volume = volume
        self.elasticity = elasticity
        self.world_characteristics = world_characteristics
        self.creature_storage = creature_storage
        # сила (сумма сил), с которой действуют на объект в данный тик
        self.force = Vector(0, 0)
        self.speed = Vector(0, 0)

    @property
    def mass(self):
        return self._mass + self.creature_storage.mass

    def get_movement(self, ticks = 1):
        # ticks - количество тиков, за которое рассчитывается перемещение
        return self.speed.multiply(ticks)

    def tick(self):
        ticks = 1
        self.speed.accumulate(
            self.force.x * ticks / self.mass,
            self.force.y * ticks / self.mass
        )
        self.speed.divide_ip(self.world_characteristics.viscosity)
        self.force.reset()
