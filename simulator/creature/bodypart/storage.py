from simulator.creature.bodypart import BaseBodypart, Body
from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN, Resources


class Storage(BaseBodypart):
    _composition = Resources(
        {
            OXYGEN: 40,
            CARBON: 20,
            HYDROGEN: 10
        }
    )
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

    @property
    def stored_resources(self) -> Resources:
        resources = Resources()
        for resource_storage in self._storage.values():
            resources[resource_storage.world_resource] += resource_storage.current
        return resources

    def add_resource_storage(self, resource: BaseWorldResource, size: float):
        """Присоединяет хранилище ресурса к общему."""

        resource_storage = ResourceStorage(resource, size, self)
        self._storage[resource] = resource_storage
        self.dependent_bodyparts.append(resource_storage)

    def add_resources(self, resources: Resources):
        for resource, amount in resources.items():
            if amount > 0:
                self._storage[resource].add(amount)
            elif amount < 0:
                raise ValueError(f"Adding resource ({resource}) must be not negative ({amount}). {self}")

    def remove_resources(self, resources: Resources):
        for resource, amount in resources.items():
            if amount > 0:
                self._storage[resource].remove(amount)
            elif amount < 0:
                raise ValueError(f"Removing resource ({resource}) must be not negative ({amount}). {self}")

    @property
    def extra_resources(self) -> Resources:
        extra_resources = Resources()
        for resource_storage in self._storage.values():
            extra_resources[resource_storage.world_resource] = resource_storage.extra
        return extra_resources

    @property
    def lack_resources(self) -> Resources:
        lack_resources = Resources()
        for resource_storage in self._storage.values():
            lack_resources[resource_storage.world_resource] = resource_storage.lack
        return lack_resources

    @property
    def fullness(self) -> Resources:
        fullness = Resources()
        for resource in self._storage.values():
            fullness[resource.world_resource] = resource.fullness
        return fullness


class ResourceStorage(BaseBodypart):
    world_resource: BaseWorldResource
    capacity: int
    required_bodypart_class = Storage
    # показывает дополнительное увеличение объема части тела (хранилища), в зависимости от вместимости
    extra_volume_coef = 0.1
    _composition = Resources(
        {
            OXYGEN: 10,
            CARBON: 5
        }
    )

    def __init__(self, world_resource: BaseWorldResource, size, required_bodypart):
        super().__init__(size, required_bodypart)

        self.world_resource = world_resource
        self.current = 0

    def __repr__(self):
        return f"{repr(self.world_resource)}Storage: {self.current}/{self.capacity}"

    @property
    def fullness(self) -> float:
        return self.current / self.capacity

    def add(self, amount: int):
        self.current += amount

    def remove(self, amount: int):
        self.current -= amount

    def reset(self):
        self.current = 0

    def destroy(self) -> Resources:
        return_resources = Resources()
        return_resources[self.world_resource] = self.current
        self.reset()
        return_resources += super(ResourceStorage, self).destroy()
        return return_resources

    @property
    def full(self) -> bool:
        return self.current >= self.capacity

    @property
    def empty(self) -> bool:
        return self.current <= 0

    @property
    def extra(self) -> int:
        if self.full:
            extra = self.current - self.capacity
        else:
            extra = 0
        return extra

    @property
    def lack(self) -> int:
        if self.empty:
            lack = -self.current
        else:
            lack = 0
        return lack

    @property
    def volume(self) -> int:
        volume = super().volume
        volume += int(self.world_resource.volume * self.capacity * self.extra_volume_coef)
        return volume

    @property
    def mass(self) -> int:
        mass = super().mass
        mass += self.world_resource.mass * self.current
        return mass
