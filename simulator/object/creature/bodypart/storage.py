from simulator.object.creature.bodypart import BaseBodypart
from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN


class ResourceStorage(BaseBodypart):
    world_resource: BaseWorldResource
    capacity: int
    _composition = {
        OXYGEN: 10,
        CARBON: 5
    }

    def __init__(self, world_resource: BaseWorldResource, size):
        super().__init__(size)

        self.world_resource = world_resource
        self.current = 0

    def __repr__(self):
        return f"{repr(self.world_resource)}: {self.current}/{self.capacity}"

    def add(self, amount):
        self.current += amount

    def remove(self, amount):
        old_current = self.current
        self.current -= amount
        if self.current < 0:
            raise ValueError(f"{self.world_resource}({self.capacity}): {old_current} - {amount} = {self.current}")

    @property
    def full(self) -> bool:
        return self.current >= self.capacity

    @property
    def empty(self) -> bool:
        return self.current <= 0

    @property
    def extra(self) -> int:
        extra = 0
        if self.full:
            extra = self.current - self.capacity
        return extra

    @property
    def volume(self) -> int:
        volume = super().volume
        volume += self.world_resource.volume * self.current
        return volume

    @property
    def mass(self) -> int:
        mass = super().mass
        mass += self.world_resource.mass * self.current
        return mass


class Storage(BaseBodypart):
    _composition = {
        OXYGEN: 40,
        CARBON: 20,
        HYDROGEN: 10
    }

    def __init__(self, size: float):
        super().__init__(size)

        self._storage: dict[BaseWorldResource, ResourceStorage] = {}

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def __repr__(self) -> str:
        string = f"{super().__repr__()}: "
        for resource in self.values():
            # string += f"{resource}, "
            string += f"{resource.world_resource.formula}: {resource.current}/{resource.capacity}, "
        if string[-2:] == ", ":
            string = string[:-2]
        return string

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def add_resource_storage(self, resource, size):
        """Присоединяет хранилище ресурса к общему."""

        self._storage[resource] = ResourceStorage(resource, size)

    def add(self, resource, amount) -> int:
        """Добавляет ресурс в хранилище."""

        self._storage[resource].add(amount)
        return self._storage[resource].extra

    def remove(self, resource, amount):
        """Убирает ресурс из хранилища."""

        self._storage[resource].remove(amount)

    @property
    def fullness(self) -> dict[BaseWorldResource, float]:
        fullness = {}
        for resource in self._storage.values():
            fullness[resource.world_resource] = resource.current / resource.capacity
        return fullness

    # если возвращает None -> все ресурсы хранятся в максимальном объеме
    @property
    def most_not_full(self) -> BaseWorldResource | None:
        minimum_resource = list(self.fullness.keys())[0]
        minimum = list(self.fullness.values())[0]
        for resource, fullness in self.fullness.items():
            if fullness < minimum:
                minimum = fullness
                minimum_resource = resource
        if minimum == 1:
            minimum_resource = None
        return minimum_resource
