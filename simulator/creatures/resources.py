import logging
from dataclasses import dataclass

from simulator.loggers.base import OBJECT_ID
from simulator.worlds.resources import BaseResource


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


class BaseResourcesStorage:
    counter = 0
    logger: logging.LoggerAdapter

    def __init__(self, creature, resources: list[tuple[BaseResource, int, int]]):
        self.id = f"{self.__class__.__name__}{self.counter}"
        self.__class__.counter += 1

        self.creature = creature

        self._storage: dict[BaseResource, BaseStoredResource] = {}
        for resource in resources:
            self.add_stored_resource(*resource)

    def __getitem__(self, item):
        return self._storage[item]

    def __iter__(self):
        return iter(self._storage)

    def items(self):
        return self._storage.items()

    def keys(self):
        return self._storage.keys()

    def values(self):
        return self._storage.values()

    def spawn(self):
        self.logger = self.creature.logger.logger.getChild(self.__class__.__name__)
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.id})

    def add_stored_resource(self, resource, capacity, current):
        """Добавляет тип ресурса в хранилище."""

        self._storage[resource] = BaseStoredResource(resource, capacity, current)

    def can_store(self, resource, number) -> bool:
        """Проверяет, может ли быть запасен ресурс."""

        return self._storage[resource].can_store(number)

    def add_to_store(self, resource, number):
        """Добавляет ресурс в хранилище."""

        old = self._storage[resource].current
        self._storage[resource].add(number)
        self.logger.info(f"{self.creature} {resource} store {old} -> {self._storage[resource].current}")

    def remove_from_store(self, resource, number):
        """Убирает ресурс из хранилища."""

        old = self._storage[resource].current
        self._storage[resource].remove(number)
        self.logger.info(f"{self.creature} {resource} store {old} -> {self._storage[resource].current}")
