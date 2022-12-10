from dataclasses import dataclass
from typing import TYPE_CHECKING

from core import models
from logger import BaseLogger
from simulator.object.base import BaseSimulationObject
from simulator.world_resource.base import BaseResource


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from simulator.object.creature.base import BaseSimulationCreature


@dataclass
class BaseStoredResource:
    world_resource: BaseResource
    capacity: int
    current: int

    def __repr__(self):
        return repr(self.world_resource)

    def add(self, number):
        self.current += number

    def remove(self, number):
        self.current -= number

    @property
    def is_full(self):
        return self.current >= self.capacity

    @property
    def is_empty(self):
        return self.current <= 0

    def can_store(self, number):
        return self.current + number <= self.capacity


class BaseSimulationStorage(BaseSimulationObject):
    db_model = models.CreatureStorage
    counter: int = 0

    def __init__(self, creature: "BaseSimulationCreature", resources: list[tuple[BaseResource, int, int]]):
        self.id = int(f"{creature.id}{self.__class__.counter}")
        self.__class__.counter += 1

        self.creature = creature
        self.logger = BaseLogger(
            f"{self.creature.world.object_id}.{self.creature.object_id}.{self.object_id}"
        )

        self._storage: dict[BaseResource, BaseStoredResource] = {}
        for resource in resources:
            self.add_stored_resource(*resource)

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def save_to_db(self):
        self.db_instance = self.db_model(creature = self.creature.db_instance)
        self.db_instance.save()

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def add_stored_resource(self, resource, capacity, current):
        """Добавляет тип ресурса в хранилище."""

        self._storage[resource] = BaseStoredResource(resource, capacity, current)

    def can_store(self, resource, number) -> bool:
        """Проверяет, может ли быть запасен ресурс."""

        return self._storage[resource].can_store(number)

    def add(self, resource, number):
        """Добавляет ресурс в хранилище."""

        self._storage[resource].add(number)

    def remove(self, resource, number):
        """Убирает ресурс из хранилища."""

        self._storage[resource].remove(number)

    @property
    def mass(self):
        mass = 0
        for world_resource, resource in self._storage.items():
            mass += world_resource.mass * resource.current
        return mass
