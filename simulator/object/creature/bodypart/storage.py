from simulator.object.creature.bodypart import BaseBodypart, Body
from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN


class Storage(BaseBodypart):
    _composition = {
        OXYGEN: 40,
        CARBON: 20,
        HYDROGEN: 10
    }
    required_bodypart_class = Body

    def __init__(self, size, required_bodypart):
        super().__init__(size, required_bodypart)

        self._storage: dict[BaseWorldResource, ResourceStorage] = {}

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def __repr__(self) -> str:
        string = f"{super().__repr__()}: "
        if len(self._storage) > 0:
            for resource in self.values():
                # string += f"{resource}, "
                string += f"{resource.world_resource.formula}: {resource.current}/{resource.capacity}, "
        else:
            string += "empty"
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

        resource_storage = ResourceStorage(resource, size, self)
        self._storage[resource] = resource_storage
        self.dependent_bodyparts.append(resource_storage)

    def add(self, resource, amount) -> int:
        """Добавляет ресурс в хранилище."""

        self._storage[resource].add(amount)
        return self._storage[resource].extra

    def remove(self, resource, amount) -> int:
        """Убирает ресурс из хранилища."""

        self._storage[resource].remove(amount)
        return self._storage[resource].lack

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


class ResourceStorage(BaseBodypart):
    world_resource: BaseWorldResource
    capacity: int
    required_bodypart_class = Storage
    _composition = {
        OXYGEN: 10,
        CARBON: 5
    }

    def __init__(self, world_resource: BaseWorldResource, size, required_bodypart):
        super().__init__(size, required_bodypart)

        self.world_resource = world_resource
        self.current = 0

    def __repr__(self):
        return f"{repr(self.world_resource)}Storage: {self.current}/{self.capacity}"

    def add(self, amount):
        self.current += amount

    def remove(self, amount):
        self.current -= amount

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
    def lack(self) -> int:
        lack = 0
        if self.empty:
            lack = 0 - self.current
        return lack

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
