import logging
from typing import TYPE_CHECKING

import pygame

from creatures.genome.base import BaseGenome
from creatures.resources import BaseResourcesStore
from loggers.base import OBJECT_ID
from worlds.position import Position
from worlds.resources import CARBON, ENERGY, HYDROGEN, LIGHT, OXYGEN


# https://adamj.eu/tech/2021/05/13/python-type-hints-how-to-fix-circular-imports/
if TYPE_CHECKING:
    from worlds.base import BaseWorld


# https://ru.wikipedia.org/wiki/%D0%A4%D0%BE%D1%82%D0%BE%D1%81%D0%B8%D0%BD%D1%82%D0%B5%D0%B7
class BaseCreature(pygame.sprite.Sprite):
    # ((consume, store, throw), (consume, store, throw), ...)
    consumption_processes = (
        (
            {OXYGEN: 2, CARBON: 2, HYDROGEN: 2, LIGHT: 2},
            {OXYGEN: 1, CARBON: 1, HYDROGEN: 1, ENERGY: 1},
            {OXYGEN: 1, CARBON: 1, HYDROGEN: 1}
        ),
    )
    counter = 0

    # position - центр существа
    def __init__(self, position: Position, world: "BaseWorld", *args):
        super().__init__(*args)

        # должен быть уникальным для всех существ в мире
        self.id = f"{self.__class__.__name__}{self.counter}"
        self.counter += 1
        self.genome = BaseGenome()
        self.position = position

        self.surface = pygame.Surface((5, 5))
        self.surface.fill((0, 0, 0))
        self.rectangle = self.surface.get_rect()
        self.rectangle.x = self.position.x - self.rectangle[2]//2
        self.rectangle.y = self.position.y - self.rectangle[3]//2

        self.world = world
        self.screen = world.screen
        self.logger = world.logger.logger.getChild(self.__class__.__name__)
        self.logger = logging.LoggerAdapter(self.logger, {OBJECT_ID: self.id})

        self.resources = BaseResourcesStore(self)

        self.logger.info(f"spawns at {self.position}")

    def __repr__(self):
        return self.id

    def draw(self):
        """Отрисовывает существо на экране."""

        self.screen.blit(self.surface, self.rectangle)

    def tick(self):
        """Симулирует жизнедеятельность за один тик."""

        if self.can_consume():
            self.consume()

    def can_consume(self) -> bool:
        can_eat = True
        for resource, number in self.consumption_processes[0][0].items():
            can_eat = can_eat and self.world.check_resource(self.position, resource, number)
        return can_eat

    def consume(self):
        """Симулирует потребление веществ существом."""

        consumption_process = self.consumption_processes[0]
        # забирает из мира ресурсы
        for resource, number in consumption_process[0].items():
            self.world.remove_resource(self.position, resource, number)
        # добавляет в свое хранилище
        for resource, number in consumption_process[1].items():
            self.resources.add_to_store(resource, number)
        # отдает ресурсы в мир
        for resource, number in consumption_process[2].items():
            self.world.add_resource(self.position, resource, number)
        self.logger.info(
            f"consume: {consumption_process[0]} | store: {consumption_process[1]} | throw {consumption_process[2]}"
        )
