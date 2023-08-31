from simulator.creature.bodypart import BaseBodypart, Body
from simulator.world_resource import BaseWorldResource, CARBON, HYDROGEN, OXYGEN, Resources


class AddToNonExistentStoragesException(Exception):
    """Исключение для Storage."""

    def __init__(self, message: str):
        super().__init__(message)
        self.resources = Resources()


class AddToDestroyedStorageException(Exception):
    """Исключение для ResourceStorage."""

    def __init__(self, world_resource: BaseWorldResource, amount: int, message: str):
        super().__init__(message)
        self.world_resource = world_resource
        self.amount = amount


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
        self._stored_resources: Resources | None = None
        self._extra_resources: Resources | None = None
        self._lack_resources: Resources | None = None
        self._fullness: Resources | None = None

    def __repr__(self) -> str:
        string = f"{super().__repr__()}: "
        if len(self._storage) > 0:
            for storage in self.values():
                if storage.destroyed:
                    string += f"{storage.world_resource.formula}: destroyed, "
                else:
                    string += f"{storage.world_resource.formula}: {storage.current}/{storage.capacity}, "
        else:
            string += "empty"
        if string[-2:] == ", ":
            string = string[:-2]
        return string

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    @property
    def stored_resources(self) -> Resources:
        if self._stored_resources is None:
            self._stored_resources = Resources()
            for resource_storage in self._storage.values():
                self._stored_resources[resource_storage.world_resource] += resource_storage.current
        return self._stored_resources

    @property
    def extra_resources(self) -> Resources:
        if self._extra_resources is None:
            self._extra_resources = Resources()
            for resource_storage in self._storage.values():
                self._extra_resources[resource_storage.world_resource] = resource_storage.extra
        return self._extra_resources

    @property
    def lack_resources(self) -> Resources:
        if self._lack_resources is None:
            self._lack_resources = Resources()
            for resource_storage in self._storage.values():
                self._lack_resources[resource_storage.world_resource] = resource_storage.lack
        return self._lack_resources

    @property
    def fullness(self) -> Resources:
        if self._fullness is None:
            self._fullness = Resources()
            for resource in self._storage.values():
                self._fullness[resource.world_resource] = resource.fullness
        return self._fullness

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def add_resource_storage(self, resource: BaseWorldResource, size: float):
        """Присоединяет хранилище ресурса к общему."""

        resource_storage = ResourceStorage(resource, size, self)
        self._storage[resource] = resource_storage
        self.dependent_bodyparts.append(resource_storage)

    def add_resources(self, resources: Resources):
        self.reset_cache()
        not_added_resources = Resources()
        for resource, amount in resources.items():
            if amount > 0:
                try:
                    self._storage[resource].add(amount)
                except AddToDestroyedStorageException as exception:
                    not_added_resources[exception.world_resource] = exception.amount
            elif amount < 0:
                raise ValueError(f"Adding resource ({resource}) must be not negative ({amount}). {self}")
        if len(not_added_resources) > 0:
            common_exception = AddToNonExistentStoragesException(f"{not_added_resources} can not be added to {self}")
            common_exception.resources = not_added_resources
            raise common_exception

    def remove_resources(self, resources: Resources):
        self.reset_cache()
        for resource, amount in resources.items():
            if amount > 0:
                self._storage[resource].remove(amount)
            elif amount < 0:
                raise ValueError(f"Removing resource ({resource}) must be not negative ({amount}). {self}")

    def reset_cache(self):
        self._stored_resources = None
        self._extra_resources = None
        self._lack_resources = None
        self._fullness = None


class ResourceStorage(BaseBodypart):
    world_resource: BaseWorldResource
    capacity: int
    required_bodypart_class = Storage
    # показывает дополнительное увеличение объема части тела (хранилища), в зависимости от вместимости
    extra_volume_coeff = 0.1
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

    def __repr__(self) -> str:
        string = f"{repr(self.world_resource)}Storage: "
        if self.destroyed:
            string += "destroyed"
        else:
            string += f"{self.current}/{self.capacity}"
        return string

    @property
    def fullness(self) -> float:
        return self.current / self.capacity

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
        volume += int(self.world_resource.volume * self.capacity * self.extra_volume_coeff)
        return volume

    @property
    def mass(self) -> int:
        mass = super().mass
        mass += self.world_resource.mass * self.current
        return mass

    def add(self, amount: int):
        if not self.destroyed:
            self.current += amount
        else:
            raise AddToDestroyedStorageException(self.world_resource, amount, f"{self}")

    def remove(self, amount: int):
        if not self.destroyed:
            self.current -= amount
        else:
            raise ValueError(f"{self}")

    def reset(self):
        self.current = 0

    def destroy(self) -> Resources:
        return_resources = super(ResourceStorage, self).destroy()
        return_resources[self.world_resource] += self.current
        self.reset()
        return return_resources
