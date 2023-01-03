from typing import Generic, Self, TypeVar, Union


class BaseWorldResource:
    counter = [0]
    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BaseBodypart.mass и BaseBodypart.volume
    volume = 1
    mass = 1

    def __init__(self, name: str, formula: str | None):
        self.hash = self.__class__.counter[0]
        self.__class__.counter[0] += 1
        self.name = name
        self.formula = formula

    def __hash__(self):
        return self.hash

    def __repr__(self):
        return self.name

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

RESOURCES_LIST = [ENERGY, OXYGEN, CARBON, HYDROGEN]
VT = TypeVar("VT", int, float)


class Resources(Generic[VT]):
    """Обертка для удобной работы с ресурсами."""

    def __init__(self, dictionary: dict[BaseWorldResource, VT] = None):
        resources = {resource: 0 for resource in RESOURCES_LIST}
        if dictionary is not None:
            for resource, amount in dictionary.items():
                resources[resource] = amount
        self._storage: dict[BaseWorldResource, VT] = resources

    def __repr__(self) -> str:
        string = f"{self.__class__.__name__}: "
        if len(self) > 0:
            for resource, amount in self._storage.items():
                string += f"{resource.formula}: {amount}, "
            if string[-2:] == ", ":
                string = string[:-2]
        else:
            string += "empty"
        return string

    def __setitem__(self, resource: BaseWorldResource, amount: VT):
        self._storage[resource] = amount

    def __getitem__(self, resource: BaseWorldResource) -> VT:
        return self._storage[resource]

    def __iadd__(self, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        other = self.get_resources(other)
        for resource, amount in self.items():
            self[resource] += other[resource]
        return self

    def __add__(self, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        other = self.get_resources(other)
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] + other[resource]
        return resources

    def __isub__(self, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        other = self.get_resources(other)
        for resource, amount in self.items():
            self[resource] -= other[resource]
        return self

    def __sub__(self, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        other = self.get_resources(other)
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] - other[resource]
        return resources

    def __mul__(self, multiplier: Union["Resources", int, float]) -> Self:
        if isinstance(multiplier, Resources):
            resources = self.resources_multiplication(multiplier)
        else:
            resources = self.number_multiplication(multiplier)
        return resources

    def __truediv__(self, divisor: Union["Resources", int, float]) -> Self:
        if isinstance(divisor, Resources):
            resources = self.resources_division(divisor)
        else:
            resources = self.number_division(divisor)
        return resources

    def __floordiv__(self, divisor: Union["Resources", int, float]) -> Self:
        return (self / divisor).round_ip()

    def __iter__(self):
        return iter(self._storage)

    def __len__(self) -> int:
        length = 0
        for amount in self._storage.values():
            if amount != 0:
                length += 1
        return length

    def sum(self) -> VT:
        total = 0
        for amount in self._storage.values():
            total += amount
        return total

    @classmethod
    def get_resources(cls, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        if isinstance(other, cls):
            resources = other
        else:
            resources = cls(other)
        return resources

    def number_division(self, divisor: int | float) -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] / divisor
        return resources

    def resources_division(self, divisor: "Resources") -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] / divisor[resource]
        return resources

    def number_multiplication(self, multiplier: int | float) -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] * multiplier
        return resources

    def resources_multiplication(self, multiplier: "Resources") -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] * multiplier[resource]
        return resources

    def items(self) -> tuple[tuple[BaseWorldResource, VT]]:
        return tuple(zip(self.keys(), self.values()))

    def keys(self) -> tuple[BaseWorldResource]:
        return tuple(self._storage.keys())

    def values(self) -> tuple[VT]:
        return tuple(amount for amount in self._storage.values())

    def round(self) -> "Resources[int]":
        resources = self.__class__()
        for resource, amount in self._storage.items():
            resources[resource] = int(amount)
        return resources

    def round_ip(self) -> "Resources[int]":
        self._storage = self.round()._storage
        return self
