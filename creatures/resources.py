import logging
from dataclasses import dataclass

from loggers.base import OBJECT_ID
from worlds.resources import BaseResource, CARBON, ENERGY, HYDROGEN, OXYGEN


@dataclass
class BaseStoredResource:
    world_resource: BaseResource
    capacity: int
    current: int

    def add(self, number):
        self.current += number

    def remove(self, number):
        self.current -= number


class BaseResourcesStore:
    counter = 0

    def __init__(self, creature):
        self.id = f"{self.__class__.__name__}{self.counter}"
        self.counter += 1

        self.creature = creature
        self.logger = creature.logger.logger.getChild(self.__class__.__name__)
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.id})

        self.store: dict[BaseResource, BaseStoredResource] = {}
        self.add_stored_resource(CARBON, 100, 50)
        self.add_stored_resource(OXYGEN, 100, 50)
        self.add_stored_resource(HYDROGEN, 100, 50)
        self.add_stored_resource(ENERGY, 100, 50)

    def add_stored_resource(self, resource, capacity, current):
        """Добавляет тип ресурса в хранилище."""
        self.store[resource] = BaseStoredResource(resource, capacity, current)

    def add_to_store(self, resource, number):
        """Добавляет ресурс в хранилище."""
        self.store[resource].add(number)
        self.logger.info(f"{number} {resource} adds to {self.creature} store")

    def remove_from_store(self, resource, number):
        """Убирает ресурс из хранилища."""
        self.store[resource].remove(number)
        self.logger.info(f"{number} {resource} removes from {self.creature} store")

    def __getitem__(self, item):
        return self.store[item]
