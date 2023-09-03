from typing import Dict, TypeVar


class BaseWorldResource:
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

    def __eq__(self, other: "BaseWorldResource") -> bool:
        return hash(self) == hash(other) and isinstance(other, self.__class__)


class EnergyResource(BaseWorldResource):
    volume = 0
    mass = 0

    def __init__(self, name):
        super().__init__(name, None)
        self.formula = self.name.lower()


ENERGY = EnergyResource("Energy")
# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
OXYGEN = BaseWorldResource("Oxygen", "O")
CARBON = BaseWorldResource("Carbon", "C")
HYDROGEN = BaseWorldResource("Hydrogen", "H")

RESOURCE_LIST = [ENERGY, OXYGEN, CARBON, HYDROGEN]
VT = TypeVar("VT", int, float)
KT = TypeVar("KT", bound = BaseWorldResource)


class Resources(Dict[KT, VT]):
    """Обертка для удобной работы с ресурсами."""

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
        for resource, amount in self.items():
            self[resource] += other[resource]
        return self

    def __add__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] + other[resource] for resource in RESOURCE_LIST})

    def __isub__(self, other: "Resources") -> "Resources":
        for resource, amount in self.items():
            self[resource] -= other[resource]
        return self

    def __sub__(self, other: "Resources") -> "Resources":
        return self.__class__({resource: self[resource] - other[resource] for resource in RESOURCE_LIST})

    def __mul__(self, multiplier: int | float) -> "Resources":
        return self.__class__({resource: self[resource] * multiplier for resource in RESOURCE_LIST})

    def __imul__(self, multiplier: int | float) -> "Resources":
        for resource, amount in self.items():
            self[resource] *= multiplier
        return self

    def __truediv__(self, divisor: int | float) -> "Resources":
        return self.__class__({resource: self[resource] / divisor for resource in RESOURCE_LIST})

    def __floordiv__(self, divisor: int | float) -> "Resources":
        return (self / divisor).round()

    def __len__(self) -> int:
        return sum([amount != 0 for amount in self.values()])

    # todo: заменить на __round__
    def round(self) -> "Resources[BaseWorldResource, int]":
        return self.__class__({resource: int(amount) for resource, amount in self.items()})
