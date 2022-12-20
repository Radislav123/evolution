import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core import models
from simulator.object.base import BaseSimulationObject
from simulator.world_resource.base import BaseWorldResource


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature


@dataclass
class BaseStoredResource:
    world_resource: BaseWorldResource
    current: int
    capacity: int
    almost_full_level = 0.8

    def __repr__(self):
        return f"{repr(self.world_resource)}: {self.current}/{self.capacity}"

    def add(self, number):
        self.current += number

    def remove(self, number):
        self.current -= number

    @property
    def almost_full(self) -> bool:
        return self.current >= self.capacity * self.almost_full_level

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

    def can_store(self, number) -> bool:
        return self.current + number <= self.capacity


class BaseSimulationStorage(BaseSimulationObject):
    db_model = models.CreatureStorage

    def __init__(self):
        self._storage: dict[BaseWorldResource, BaseStoredResource] = {}

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def __repr__(self) -> str:
        string = ""
        for resource in self.values():
            string += f"{resource}\n"
        string = string[:-1]
        return string

    @property
    def deprecation_warning_message(self) -> str:
        return f"{self.__class__.__name__} is not completely {BaseSimulationObject.__name__}"

    @property
    def object_id(self):
        warnings.warn(self.deprecation_warning_message, DeprecationWarning)
        return

    def start(self, creature: "BaseSimulationCreature", *args, **kwargs):
        super().start(creature, *args, **kwargs)

    def stop(self, creature: "BaseSimulationCreature", *args, **kwargs):
        super().stop(creature, *args, **kwargs)

    def release_logs(self):
        warnings.warn(self.deprecation_warning_message, DeprecationWarning)

    def save_to_db(self, creature: "BaseSimulationCreature"):
        self.db_instance = self.db_model(creature = creature.db_instance)
        self.db_instance.save()
        # todo: сохранять ресурсы models.StoredResource

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def add_stored_resource(self, resource, current, capacity):
        """Добавляет тип ресурса в хранилище."""

        self._storage[resource] = BaseStoredResource(resource, current, capacity)

    def can_store(self, resource, number) -> bool:
        """Проверяет, может ли быть запасен ресурс."""

        return self._storage[resource].can_store(number)

    def add(self, resource, number) -> int:
        """Добавляет ресурс в хранилище."""

        self._storage[resource].add(number)
        return self._storage[resource].extra

    def remove(self, resource, number):
        """Убирает ресурс из хранилища."""

        self._storage[resource].remove(number)

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

    @property
    def mass(self):
        mass = 0
        for world_resource, resource in self._storage.items():
            mass += world_resource.mass * resource.current
        return mass
