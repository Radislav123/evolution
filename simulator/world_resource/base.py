from collections import defaultdict
from typing import Callable, Iterable, Iterator, TypeVar

from core.service import ObjectDescriptionReader
from evolution import settings


# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
class WorldResource(int):
    counter = 0
    max_formula_length = 0
    operators_overloaded = False

    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BodypartInterface.mass и BodypartInterface.volume
    # объем

    def __new__(cls, name: str, formula: str, mass: float, volume: float) -> "WorldResource":
        obj = int.__new__(cls, cls.counter)
        cls.counter += 1
        obj.name = name
        obj.formula = formula
        obj.mass = mass
        obj.volume = volume
        cls.max_formula_length = max(obj.max_formula_length, len(obj.formula))

        if not cls.operators_overloaded:
            not_allowed_operators = (
                "__add__", "__iadd__",
                "__sub__", "__isub__",
                "__mul__", "__imul__",
                "__truediv__", "__itruediv__",
                "__floordiv__", "__ifloordiv__",
                "__round__",
                "__neg__",
            )
            for name in not_allowed_operators:
                setattr(cls, name, cls.not_implemented_operator_factory(name))

        return obj

    def __repr__(self) -> str:
        return self.name

    @staticmethod
    def not_implemented_operator_factory(name: str) -> Callable[["WorldResource", ...], None]:
        def not_implemented_operator(self, *_) -> None:
            raise NotImplementedError(f"{name} is not available for {self} resource.")

        return not_implemented_operator

    @property
    def sort_key(self) -> str:
        return self.formula.rjust(self.max_formula_length + 1, '_')


# {resource.name: resource}
RESOURCE_DICT = dict(
    sorted(
        ObjectDescriptionReader[WorldResource]().read_folder_to_dict(
            settings.WORLD_RESOURCE_DESCRIPTIONS_PATH,
            WorldResource
        ).items(),
        key = lambda x: x[1].sort_key
    )
)
RESOURCE_LIST = [x for x in RESOURCE_DICT.values()]
ENERGY = RESOURCE_DICT["energy"]

VT = TypeVar("VT", int, float)


class Resources(defaultdict[WorldResource, VT]):
    """Обертка-контейнер для удобной работы с ресурсами."""

    def __init__(self, *args):
        # for resource in RESOURCE_LIST:
        #     self[resource] = 0
        if args and callable(args[0]):
            super().__init__(*args)
        else:
            super().__init__(int, *args)

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

    def __add__(self, other: "Resources") -> "Resources":
        new = self.copy()
        new += other
        return new

    def __iadd__(self, other: "Resources") -> "Resources":
        for resource, amount in other.items():
            self[resource] += amount
        return self

    def __sub__(self, other: "Resources") -> "Resources":
        new = self.copy()
        new -= other
        return new

    def __isub__(self, other: "Resources") -> "Resources":
        for resource, amount in other.items():
            self[resource] -= amount
        return self

    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: amount * multiplier for resource, amount in self.items()})

    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource, amount in self.items():
            self[resource] = amount * multiplier
        return self

    def __truediv__(self, divisor: int | float) -> "Resources[float]":
        return self.__class__({resource: amount / divisor for resource, amount in self.items()})

    def __itruediv__(self, divisor: int | float) -> "Resources[float]":
        for resource, amount in self.items():
            self[resource] = amount / divisor
        return self

    def __floordiv__(self, divisor: int | float) -> "Resources[int]":
        return self.__class__({resource: amount // divisor for resource, amount in self.items()})

    def __ifloordiv__(self, divisor: int | float) -> "Resources[int]":
        for resource, amount in self.items():
            self[resource] = amount // divisor
        return self

    def __len__(self) -> int:
        return sum(amount != 0 for amount in self.values())

    def __iter__(self) -> Iterator[WorldResource]:
        return iter(resource for resource, amount in self.items() if amount != 0)

    def __neg__(self) -> "Resources[VT]":
        return self.__class__({resource: -amount for resource, amount in self.items()})

    # не заменять на __round__, потому что вне зависимости от того, какой возвращаемый тип будет указан в методе,
    # возвращаемое значение из round() всегда считается int-ом
    def round(self) -> "Resources[int]":
        return self.__class__({resource: int(amount) for resource, amount in self.items()})

    def iround(self) -> "Resources[int]":
        for resource, amount in self.items():
            self[resource] = round(amount)
        return self

    @classmethod
    def sum(cls, resources_iterable: Iterable["Resources"]) -> "Resources":
        resources_sum = Resources()
        for resources in resources_iterable:
            resources_sum += resources
        return resources_sum

    def fill_all(self, amount: int | float) -> None:
        for resource in RESOURCE_LIST:
            self[resource] = amount
