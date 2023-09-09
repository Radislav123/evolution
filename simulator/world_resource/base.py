from typing import Dict, Iterable, Iterator, TypeVar

from core.service import ObjectDescriptionReader
from evolution import settings


# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
class WorldResource(int):
    counter = [0]
    max_formula_length = [0]

    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BodypartInterface.mass и BodypartInterface.volume
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
# todo: убрать отсюда явные ресурсы (оставить пока что энергию)
ENERGY = RESOURCE_DICT["energy"]

VT = TypeVar("VT", int, float)


# todo: проверить будет ли Resources быстрее работать, если унаследовать его от collections.Counter
class Resources(Dict[WorldResource, VT]):
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

    def __mul__(self, multiplier: VT) -> "Resources":
        return self.__class__({resource: self[resource] * multiplier for resource in RESOURCE_LIST})

    def __imul__(self, multiplier: VT) -> "Resources":
        for resource in RESOURCE_LIST:
            self[resource] *= multiplier
        return self

    def __truediv__(self, divisor: VT) -> "Resources[float]":
        return self.__class__({resource: self[resource] / divisor for resource in RESOURCE_LIST})

    def __floordiv__(self, divisor: VT) -> "Resources[int]":
        return self.__class__({resource: self[resource] // divisor for resource in RESOURCE_LIST})

    def __len__(self) -> int:
        return sum(amount != 0 for amount in self.values())

    def __iter__(self) -> Iterator[WorldResource]:
        return iter(resource for resource, amount in self.items() if amount != 0)

    # не заменять на __round__, потому что вне зависимости от того, какой возвращаемый тип будет указан в методе,
    # возвращаемое значение из round() всегда считается int-ом
    def round(self) -> "Resources[WorldResource, int]":
        return self.__class__({resource: int(amount) for resource, amount in self.items()})

    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        temp_iterable = list(resources_iterable)
        return Resources({resource: sum(x[resource] for x in temp_iterable) for resource in RESOURCE_LIST})
