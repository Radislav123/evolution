from dataclasses import dataclass
from typing import Generic, Self, TypeVar, Union
from evolution import settings


@dataclass
class BaseWorldResource:
    abstract = True
    name: str
    formula: str
    # если будет принято решение сделать mass или volume не целым, решить,
    # что делать с атрибутами BaseBodypart.mass и BaseBodypart.volume
    volume = 1
    mass = 1

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


@dataclass(eq = False, repr = False)
class EnergyResource(BaseWorldResource):
    formula: str = None
    volume = 0
    mass = 0

    def __init__(self, name):
        super().__init__(name, self.formula)
        self.formula = self.name.lower()


ENERGY = EnergyResource("Energy")
# https://ru.wikipedia.org/wiki/%D0%A5%D0%B8%D0%BC%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B9_%D1%81%D0%BE%D1%81%D1%82%D0%B0%D0%B2_%D1%87%D0%B5%D0%BB%D0%BE%D0%B2%D0%B5%D0%BA%D0%B0
OXYGEN = BaseWorldResource("Oxygen", "O")
CARBON = BaseWorldResource("Carbon", "C")
HYDROGEN = BaseWorldResource("Hydrogen", "H")

RESOURCES_LIST = [ENERGY, OXYGEN, CARBON, HYDROGEN]
VT = TypeVar("VT", int, float)


class ResourceAmount(Generic[VT]):
    def __init__(self, amount: Union["ResourceAmount", VT]):
        if settings.DEBUG:
            self.check_type(amount)
        self.amount = self.get_amount(amount)

    def __repr__(self) -> str:
        return f"{self.amount}"

    def __iadd__(self, other: Union["ResourceAmount", int, float]) -> Self:
        self.amount += self.get_amount(other)
        return self

    def __add__(self, other: Union["ResourceAmount", int, float]) -> Self:
        return self.__class__(self.amount + self.get_amount(other))

    def __isub__(self, other: Union["ResourceAmount", int, float]) -> Self:
        self.amount -= self.get_amount(other)
        return self

    def __sub__(self, other: Union["ResourceAmount", int, float]) -> Self:
        return self.__class__(self.amount - self.get_amount(other))

    def __mul__(self, other: Union["ResourceAmount", int, float]) -> Self:
        return self.__class__(self.amount * self.get_amount(other))

    def __truediv__(self, other: Union["ResourceAmount", int, float]) -> Self:
        return self.__class__(self.amount / self.get_amount(other))

    def __floordiv__(self, other: Union["ResourceAmount", int, float]) -> Self:
        return (self / other).round_ip()

    def __eq__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount == self.get_amount(other)

    def __ne__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount != self.get_amount(other)

    def __lt__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount < self.get_amount(other)

    def __le__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount <= self.get_amount(other)

    def __gt__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount > self.get_amount(other)

    def __ge__(self, other: Union["ResourceAmount", int, float]) -> bool:
        return self.amount >= self.get_amount(other)

    def __neg__(self) -> Self:
        return self.__class__(-self.amount)

    @classmethod
    def check_type(cls, amount: Union["ResourceAmount", int, float]):
        if not (isinstance(amount, cls) or isinstance(amount, int) or isinstance(amount, float)):
            raise TypeError(f"amount ({amount} must be {cls.__name__} int or float)")

    @classmethod
    def get_amount(cls, other: Union["ResourceAmount", int, float]) -> int | float:
        if isinstance(other, cls):
            other_amount = other.amount
        else:
            other_amount = other
        return other_amount

    @classmethod
    def get_resource_amount(cls, other: Union["ResourceAmount", int, float]) -> Self:
        if isinstance(other, cls):
            other_amount = ResourceAmount(other.amount)
        else:
            # noinspection PyTypeChecker
            other_amount = ResourceAmount(other)
        return other_amount

    def round(self) -> "ResourceAmount[int]":
        return self.__class__[int](int(self.amount))

    def round_ip(self) -> "ResourceAmount[int]":
        self.amount = int(self.amount)
        return self


class Resources(Generic[VT]):
    """Обертка для удобной работы с ресурсами."""

    def __init__(self, dictionary: dict[BaseWorldResource, VT] | dict[BaseWorldResource, ResourceAmount[VT]] = None):
        resources = {resource: ResourceAmount[VT](0) for resource in RESOURCES_LIST}
        if dictionary is not None:
            for resource, amount in dictionary.items():
                resources[resource] = ResourceAmount.get_resource_amount(amount)
        self._storage: dict[BaseWorldResource, ResourceAmount] = resources

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

    def __setitem__(self, resource: BaseWorldResource, amount: ResourceAmount | VT):
        self._storage[resource] = ResourceAmount(amount)

    def __getitem__(self, resource: BaseWorldResource) -> ResourceAmount:
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

    def __truediv__(self, divisor: Union["Resources", ResourceAmount, int, float]) -> Self:
        if isinstance(divisor, Resources):
            resources = self.resources_division(divisor)
        else:
            resources = self.number_division(divisor)
        return resources

    def __floordiv__(self, divisor: Union["Resources", ResourceAmount, int, float]) -> Self:
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
            total += amount.amount
        return total

    @classmethod
    def get_resources(cls, other: Union["Resources", dict[BaseWorldResource, int | float]]) -> Self:
        if isinstance(other, cls):
            resources = other
        else:
            resources = cls(other)
        return resources

    def number_division(self, divisor: ResourceAmount | int | float) -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] / divisor
        return resources

    def resources_division(self, divisor: "Resources") -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] / divisor[resource]
        return resources

    def number_multiplication(self, multiplier: ResourceAmount | int | float) -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] * multiplier
        return resources

    def resources_multiplication(self, multiplier: "Resources") -> Self:
        resources = self.__class__()
        for resource, amount in self.items():
            resources[resource] = self[resource] * multiplier[resource]
        return resources

    def items(self) -> tuple[tuple[BaseWorldResource, ResourceAmount]]:
        return tuple(zip(self.keys(), self.values()))

    def keys(self) -> tuple[BaseWorldResource]:
        return tuple(self._storage.keys())

    def values(self) -> tuple[ResourceAmount]:
        return tuple(amount for amount in self._storage.values())

    def round(self) -> "Resources[int]":
        resources = self.__class__()
        for resource, amount in self._storage.items():
            resources[resource] = amount.round()
        return resources

    def round_ip(self) -> "Resources[int]":
        self._storage = self.round()._storage
        return self
