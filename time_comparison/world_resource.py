import datetime
import enum
import random
from typing import Callable


class WorldResourceOld:
    counter = [0]
    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BaseBodypart.mass и BaseBodypart.volume
    # объем
    volume = 1
    mass = 1

    def __init__(self, name: str, formula: str | None):
        self.hash = self.__class__.counter[0]
        self.__class__.counter[0] += 1
        self.name = name
        self.formula = formula

    def __repr__(self):
        return self.name

    def __hash__(self):
        return self.hash

    def __eq__(self, other: "WorldResourceOld") -> bool:
        return hash(self) == hash(other) and isinstance(other, self.__class__)


OXYGEN = WorldResourceOld("Oxygen", "O")
CARBON = WorldResourceOld("Carbon", "C")
HYDROGEN = WorldResourceOld("Hydrogen", "H")


class WorldResourceEnum(enum.Enum):
    OXYGEN = 0
    CARBON = 1
    HYDROGEN = 2


class WorldResourceInt(int):
    counter = [0]

    def __new__(cls, name: str, formula) -> "WorldResourceInt":
        obj = int.__new__(cls, cls.counter[0])
        cls.counter[0] += 1
        obj.name = name
        obj.formula = formula
        return obj


OXYGEN_INT = WorldResourceInt("Oxygen", "O")
CARBON_INT = WorldResourceInt("Carbon", "C")
HYDROGEN_INT = WorldResourceInt("Hydrogen", "H")


def random_resources() -> tuple[WorldResourceOld, WorldResourceEnum, WorldResourceInt]:
    resources_old = {0: OXYGEN, 1: CARBON, 2: HYDROGEN}
    resources_int = {0: OXYGEN_INT, 1: CARBON_INT, 2: CARBON_INT}

    borders = (0, len(resources_old) - 1)
    index = random.randint(*borders)

    return resources_old[index], WorldResourceEnum(index), resources_int[index]


TEST_DATA_LENGTH = 1000000
TEST_DATA = tuple(random_resources() for _ in range(TEST_DATA_LENGTH))


def timer(function: Callable, index: int) -> datetime.timedelta:
    start = datetime.datetime.now()
    for data in TEST_DATA:
        function(data[index])
    finish = datetime.datetime.now()
    return finish - start


def test(a) -> int:
    return hash(a)


times = [
    ("old", timer(test, 0)),
    ("enum", timer(test, 1)),
    ("int", timer(test, 2))
]
times.sort(key = lambda x: x[1])

print("--------------------------")
for k, v in times:
    print(f"{k}: \t{v} \tx{v / times[0][1]}")
