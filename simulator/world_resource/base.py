from typing import Dict, Iterator, TypeVar

from core.service import ObjectDescriptionReader
from evolution import settings


# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
class WorldResource(int):
    counter = [0]
    max_formula_length = [0]

    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BaseBodypart.mass и BaseBodypart.volume
    # объем

    def __new__(cls, name: str, formula: str, mass: float, volume: float) -> "WorldResource":
        obj = int.__new__(cls, cls.counter[0])
        cls.counter[0] += 1
        obj.name = name
        obj.formula = formula
        obj.mass = mass
        obj.volume = volume
        obj.max_formula_length[0] = max(obj.max_formula_length[0], len(obj.formula))
        return obj

    def __repr__(self) -> str:
        return self.name

    @property
    def sort_key(self) -> str:
        return self.formula.rjust(self.max_formula_length[0] + 1, '_')


# noinspection PyTypeChecker
RESOURCE_DICT = dict(
    sorted(
        ObjectDescriptionReader[WorldResource]().read_folder_to_dict(
            settings.WORLD_RESOURCE_JSON_PATH, WorldResource
        ).items(),
        key = lambda x: x[1].sort_key
    )
)
RESOURCE_LIST = [x for x in RESOURCE_DICT.values()]
OXYGEN = RESOURCE_DICT["Oxygen"]
CARBON = RESOURCE_DICT["Carbon"]
HYDROGEN = RESOURCE_DICT["Hydrogen"]
ENERGY = RESOURCE_DICT["Energy"]

KT = TypeVar("KT", bound = WorldResource)
VT = TypeVar("VT", int, float)


class Resources(Dict[KT, VT]):
    """Обертка-контейнер для удобной работы с ресурсами."""

    def __init__(self, *args, **kwargs):
        for resource in RESOURCE_LIST:
            self[resource] = 0
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:
        string = f"{self.__class__.__name__}: "
        if len(self) > 0:
            for resource, amount in self.items():
                string += f"{resource.formula}: {amount}, "
            if string[-2:] == ", ":
                string = string[:-2]
        else:
            string += "empty"
        return string

    def __iadd__(self, other: "Resources") -> "Resources":
        for resource in RESOURCE_LIST:
            self[resource] += other[resource]
        return self

    def __add__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] + other[resource] for resource in RESOURCE_LIST})

    def __isub__(self, other: "Resources") -> "Resources":
        for resource in RESOURCE_LIST:
            self[resource] -= other[resource]
        return self

    def __sub__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] - other[resource] for resource in RESOURCE_LIST})

    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: self[resource] * multiplier for resource in RESOURCE_LIST})

    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource in RESOURCE_LIST:
            self[resource] *= multiplier
        return self

    def __truediv__(self, divisor: int | float) -> "Resources":
        return self.__class__({resource: self[resource] / divisor for resource in RESOURCE_LIST})

    def __floordiv__(self, divisor: int | float) -> "Resources":
        return (self / divisor).round()

    def __len__(self) -> int:
        return sum(amount != 0 for amount in self.values())

    def __iter__(self) -> Iterator[WorldResource]:
        return iter(resource for resource, amount in self.items() if amount != 0)

    # todo: заменить на __round__
    def round(self) -> "Resources[WorldResource, int]":
        return self.__class__({resource: int(amount) for resource, amount in self.items()})
